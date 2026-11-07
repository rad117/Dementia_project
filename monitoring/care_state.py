"""
care_state.py
-------------
Temporal state machine + risk classification.

A single clip cannot tell you the gas was left on unattended, or that someone
has forgotten what they were doing. Those are patterns ACROSS clips. This
module holds the state that makes them detectable:

  - how long each appliance has been on
  - how long the person has been out of view
  - how long they have been on the floor
  - which activities were started and abandoned
  - how often the same activity repeats without completing

Risk levels
  CRITICAL  act now, likely emergency services
  HIGH      caregiver should attend within minutes
  MEDIUM    check in, log for the care record
  LOW       normal, log only
"""

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta


CRITICAL, HIGH, MEDIUM, LOW = "CRITICAL", "HIGH", "MEDIUM", "LOW"

HEAT_SOURCES = {"burner", "stove", "oven", "toaster", "kettle", "microwave"}


def _duration(secs):
    """'45 s' under a minute, else whole minutes ('0 min' read as a bug
    with the short demo thresholds)."""
    secs = int(secs)
    return f"{secs} s" if secs < 60 else f"{secs // 60} min"


@dataclass
class RiskEvent:
    level: str
    kind: str
    summary: str          # what a caregiver reads
    evidence: str         # why the system thinks so
    action: str           # what to do
    at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self):
        return {
            "at": self.at, "level": self.level, "kind": self.kind,
            "summary": self.summary, "evidence": self.evidence,
            "action": self.action,
        }


class CareState:
    """
    Feed it observations from NurseObserver. It returns risk events.

    Thresholds are in seconds and deliberately conservative for a first
    deployment -- tune them against the person's actual routine.
    """

    @classmethod
    def demo(cls):
        """
        Short thresholds for a live demonstration. Every rule fires within
        seconds instead of minutes. NOT for real deployment -- these numbers
        will produce constant false alarms in an actual home.
        """
        return cls(
            unattended_heat_s=20,
            unattended_water_s=20,
            absence_concern_s=25,
            floor_alert_s=6,
            repetition_window_s=60,
            repetition_count=3,
            cooldown_s=30,
        )

    def __init__(
        self,
        unattended_heat_s: int = 180,        # burner on, nobody there
        unattended_water_s: int = 300,
        absence_concern_s: int = 900,        # 15 min out of view
        floor_alert_s: int = 20,             # on floor this long = not deliberate
        night_start_hour: int = 23,
        night_end_hour: int = 6,
        repetition_window_s: int = 480,
        repetition_count: int = 4,
        cooldown_s: int = 300,               # don't repeat the same alert
    ):
        self.unattended_heat_s = unattended_heat_s
        self.unattended_water_s = unattended_water_s
        self.absence_concern_s = absence_concern_s
        self.floor_alert_s = floor_alert_s
        self.night_start_hour = night_start_hour
        self.night_end_hour = night_end_hour
        self.repetition_window_s = repetition_window_s
        self.repetition_count = repetition_count
        self.cooldown_s = cooldown_s

        # persistent state
        self.heat_on_since = {}          # appliance -> datetime
        self.water_on_since = None
        self.person_last_seen = None
        self.floor_since = None
        self.fall_witnessed_at = None
        self.door_open_since = None

        self.activity_log = deque(maxlen=200)   # (datetime, activity)
        self.abandoned = {}                     # activity -> datetime started
        self.last_alert_at = {}                 # kind -> datetime
        self.history = deque(maxlen=50)

    # ------------------------------------------------------------------

    def update(self, obs: dict, now: datetime = None) -> list:
        """Ingest one observation, return a list of RiskEvent."""
        now = now or datetime.now()
        events = []

        person = bool(obs.get("person_present"))
        if person:
            self.person_last_seen = now

        self._track_appliances(obs, now)
        self._track_floor(obs, person, now)
        self._track_activity(obs, person, now)

        events += self._check_immediate(obs, person, now)
        events += self._check_unattended(person, now)
        events += self._check_absence(now)
        events += self._check_repetition(now)
        events += self._check_night(obs, person, now)

        events = [e for e in events if self._not_muted(e, now)]
        for e in events:
            self.last_alert_at[e.kind] = now

        self.history.append((now, obs, [e.to_dict() for e in events]))
        return events

    # ------------------------------------------------------------------
    # state tracking

    def _track_appliances(self, obs, now):
        seen_on = set()
        for app in obs.get("appliances") or []:
            name = str(app.get("name", "")).lower()
            state = str(app.get("state", "unknown")).lower()
            if name in HEAT_SOURCES and state == "on":
                seen_on.add(name)
                self.heat_on_since.setdefault(name, now)
            elif name in HEAT_SOURCES and state == "off":
                self.heat_on_since.pop(name, None)
        # an appliance reported "unknown" keeps its previous timer running;
        # only an explicit "off" clears it. Safer direction to fail in.

        if obs.get("water_running"):
            self.water_on_since = self.water_on_since or now
        else:
            self.water_on_since = None

        if obs.get("door_open"):
            self.door_open_since = self.door_open_since or now
        else:
            self.door_open_since = None

    def _track_floor(self, obs, person, now):
        if person and (obs.get("on_floor") or obs.get("posture") == "lying"):
            self.floor_since = self.floor_since or now
        else:
            self.floor_since = None

    def _track_activity(self, obs, person, now):
        activity = (obs.get("activity") or "none").strip().lower()
        if not person or activity in ("none", "", "unknown"):
            return
        self.activity_log.append((now, activity))
        self.abandoned[activity] = self.abandoned.get(activity, now)

    # ------------------------------------------------------------------
    # rules

    def _check_immediate(self, obs, person, now):
        out = []

        # A witnessed fall fires immediately -- no dwell timer. A fall lasts
        # 1-2 seconds; requiring seconds of floor time misses it entirely,
        # and misses it completely if the person falls out of frame.
        if person and (obs.get("fall_in_progress") or obs.get("sudden_descent")):
            self.fall_witnessed_at = now
            out.append(RiskEvent(
                CRITICAL, "fall_event",
                "A fall was observed.",
                f"fall_in_progress={obs.get('fall_in_progress')}, "
                f"sudden_descent={obs.get('sudden_descent')}, "
                f"posture={obs.get('posture')}, location={obs.get('location')}",
                "Attend immediately. Do not move them if they report neck, "
                "back or hip pain -- call for medical help.",
            ))

        # Fell, then disappeared from view. Worse than staying visible, not better.
        if not person and self.fall_witnessed_at and \
                (now - self.fall_witnessed_at).total_seconds() < 120:
            out.append(RiskEvent(
                CRITICAL, "fall_then_lost",
                "A fall was seen and the person is no longer visible.",
                f"fall at {self.fall_witnessed_at:%H:%M:%S}, now out of frame",
                "Attend immediately. They may be down outside the camera's view.",
            ))

        if obs.get("visible_smoke_or_flame"):
            out.append(RiskEvent(
                CRITICAL, "fire",
                "Smoke or flame visible in the room.",
                "Observer reported visible smoke or open flame.",
                "Call emergency services now. Do not wait to verify.",
            ))

        if self.floor_since:
            secs = (now - self.floor_since).total_seconds()
            motion = obs.get("motion", "unknown")
            if secs >= self.floor_alert_s and motion in ("none", "still"):
                out.append(RiskEvent(
                    CRITICAL, "fall_motionless",
                    f"On the floor and not moving for {int(secs)}s.",
                    f"posture={obs.get('posture')}, on_floor=True, motion={motion}",
                    "Attend immediately. Treat as a fall until confirmed otherwise.",
                ))
            elif secs >= self.floor_alert_s:
                out.append(RiskEvent(
                    HIGH, "fall",
                    f"On the floor for {int(secs)}s, still moving.",
                    f"posture={obs.get('posture')}, motion={motion}",
                    "Attend now and help them up; check for injury.",
                ))

        if person and obs.get("unsteady_or_swaying"):
            out.append(RiskEvent(
                MEDIUM, "unsteady",
                "Appears unsteady on their feet.",
                f"location={obs.get('location')}",
                "Check in. Look for trip hazards and consider a seated task.",
            ))

        if person and obs.get("sharp_or_hot_object_in_hand") and \
                obs.get("motion") == "active" and obs.get("unsteady_or_swaying"):
            out.append(RiskEvent(
                HIGH, "unsafe_object",
                "Handling something sharp or hot while unsteady.",
                f"hands={obs.get('hands')}",
                "Attend and take over the task if appropriate.",
            ))

        return out

    def _check_unattended(self, person, now):
        out = []
        if person:
            return out

        for name, since in self.heat_on_since.items():
            secs = (now - since).total_seconds()
            if secs >= self.unattended_heat_s:
                out.append(RiskEvent(
                    HIGH, f"unattended_heat_{name}",
                    f"The {name} has been on and unattended for {_duration(secs)}.",
                    f"{name} state=on for {_duration(secs)}; no person in view.",
                    f"Attend now and turn the {name} off.",
                ))

        if self.water_on_since:
            secs = (now - self.water_on_since).total_seconds()
            if secs >= self.unattended_water_s:
                out.append(RiskEvent(
                    MEDIUM, "unattended_water",
                    f"Tap running unattended for {_duration(secs)}.",
                    f"water_running=True for {_duration(secs)}",
                    "Check for overflow and turn the tap off.",
                ))

        return out

    def _check_absence(self, now):
        if not self.person_last_seen:
            return []
        secs = (now - self.person_last_seen).total_seconds()
        if secs < self.absence_concern_s:
            return []
        return [RiskEvent(
            MEDIUM, "prolonged_absence",
            f"Not seen in the monitored area for {_duration(secs)}.",
            f"last seen {_duration(secs)} ago",
            "Check where they are. Confirm they have not left the home.",
        )]

    def _check_repetition(self, now):
        """
        Repetition and abandonment -- the observable signature of
        'forgot what they were doing'.
        """
        out = []
        cutoff = now - timedelta(seconds=self.repetition_window_s)
        recent = [a for t, a in self.activity_log if t >= cutoff]
        if not recent:
            return out

        counts = {}
        for a in recent:
            counts[a] = counts.get(a, 0) + 1

        for activity, n in counts.items():
            if n >= self.repetition_count and len(set(recent)) <= 3:
                out.append(RiskEvent(
                    MEDIUM, f"repetition_{activity[:24]}",
                    f"Has repeated '{activity}' {n} times in "
                    f"{_duration(self.repetition_window_s)} without finishing.",
                    f"activity log: {recent[-8:]}",
                    "Check in gently. Offer to help complete the task, or "
                    "redirect to something else.",
                ))

        # Task abandoned while a heat source is still on
        if self.heat_on_since and recent:
            latest = recent[-1]
            cooking_words = ("cook", "stir", "fry", "boil", "pan", "pot", "kettle")
            started_cooking = any(
                w in a for _, a in self.activity_log for w in cooking_words
            )
            if started_cooking and not any(w in latest for w in cooking_words):
                out.append(RiskEvent(
                    MEDIUM, "task_switch_heat_on",
                    f"Moved on to '{latest}' while a heat source is still on.",
                    f"heat on: {list(self.heat_on_since)}",
                    "Prompt them about the cooking, or turn it off yourself.",
                ))

        return out

    def _check_night(self, obs, person, now):
        hour = now.hour
        is_night = hour >= self.night_start_hour or hour < self.night_end_hour
        if not (is_night and person):
            return []

        out = []
        if obs.get("motion") == "active" and obs.get("posture") in ("standing", "upright"):
            out.append(RiskEvent(
                MEDIUM, "night_activity",
                f"Up and moving about at {now:%H:%M}.",
                f"activity={obs.get('activity')}, location={obs.get('location')}",
                "Check in. Night wandering raises fall and exit risk.",
            ))

        if self.door_open_since:
            out.append(RiskEvent(
                HIGH, "night_door_open",
                f"An external door is open at {now:%H:%M}.",
                f"door open since {self.door_open_since:%H:%M:%S}",
                "Attend now. Confirm they have not left the home.",
            ))

        return out

    # ------------------------------------------------------------------

    def _not_muted(self, event: RiskEvent, now) -> bool:
        """Suppress a repeat of the same alert kind within the cooldown."""
        last = self.last_alert_at.get(event.kind)
        if last is None:
            return True
        # CRITICAL always gets through
        if event.level == CRITICAL:
            return True
        return (now - last).total_seconds() >= self.cooldown_s

    def status(self) -> dict:
        """Current standing state, for a dashboard or /latest endpoint."""
        now = datetime.now()
        return {
            "heat_on": {
                k: int((now - v).total_seconds()) for k, v in self.heat_on_since.items()
            },
            "water_running_s": int((now - self.water_on_since).total_seconds())
            if self.water_on_since else 0,
            "seconds_since_seen": int((now - self.person_last_seen).total_seconds())
            if self.person_last_seen else None,
            "on_floor_s": int((now - self.floor_since).total_seconds())
            if self.floor_since else 0,
            "recent_activities": [a for _, a in list(self.activity_log)[-6:]],
        }