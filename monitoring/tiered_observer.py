"""Tiered observer: cheap pose model first, vision model only when it matters.

    every clip ........ PoseObserver (CPU, free): person? posture? fall?
    only if needed .... VLM (GPU, expensive): confirm a fall, read appliances

When the VLM is called:

* the pose tier sees something odd (fall, on the floor, lying, bent over,
  unsteady), or the person has just left the room;
* every ``vlm_active_interval_s`` while someone is moving about or a hazard is
  already flagged, because that is when a stove or tap can change;
* otherwise every ``vlm_interval_s``.

In between, pose-only observations carry the last VLM reading of the stove, tap
and door forward, so CareState's timers keep counting instead of being reset.

A pose model cannot tell a bed from the floor, so lying down alone is not
reported as being on the floor. It counts as on the floor only after a fall or a
sharp drop was seen, within a clip or between two clips, or when the VLM says so.
Once the VLM has seen someone lying somewhere other than the floor, the same
rest stops counting as odd, so a long sleep does not call the VLM every 30 s.

If the VLM is missing or fails, or its reply cannot be read, pose-only monitoring
carries on and the last good scene reading is kept.
"""

import time

from monitoring.nurse_observer import EMPTY_OBSERVATION
from monitoring.pose_observer import SUDDEN_DROP

# Fields only the VLM can fill; carried forward between VLM looks.
CARRIED = ("appliances", "water_running", "door_open", "location")
RETRY_AFTER_FAILURE_S = 300
UPRIGHT_POSTURES = ("standing", "sitting", "upright")
# A drop is only compared across clips when the upright reading is this recent;
# clips are a few seconds apart, and older readings say nothing about a fall.
CROSS_CLIP_WINDOW_S = 15.0


def is_odd(obs: dict) -> bool:
    return bool(
        obs.get("fall_in_progress") or obs.get("sudden_descent") or obs.get("on_floor")
        or obs.get("unsteady_or_swaying") or obs.get("posture") in ("lying", "bent_over")
    )


def scene_has_hazard(scene: dict) -> bool:
    return bool(
        scene.get("water_running") or scene.get("door_open")
        or any(str(a.get("state", "")).lower() == "on" for a in scene.get("appliances") or [])
    )


class TieredObserver:
    def __init__(self, pose, vlm_factory=None, vlm_interval_s: float = 600.0,
                 odd_recheck_s: float = 30.0, vlm_active_interval_s: float = 120.0,
                 clock=time.monotonic):
        self._pose = pose
        self._vlm_factory = vlm_factory
        self._vlm = None
        self._vlm_failed_at = float("-inf")
        self.vlm_status = "disabled" if vlm_factory is None else "not_loaded"
        self.vlm_error: str | None = None
        self.vlm_interval_s = vlm_interval_s
        self.vlm_active_interval_s = vlm_active_interval_s
        self.odd_recheck_s = odd_recheck_s
        self._clock = clock
        self._last_vlm = float("-inf")
        self._scene = {k: EMPTY_OBSERVATION[k] for k in CARRIED}
        self._was_present = False
        self._down = False            # a fall was seen and they have not got up
        self._rest_confirmed = False  # VLM saw them lying, but not on the floor
        self._upright_hip: float | None = None
        self._upright_at = float("-inf")
        self.pose_clips = 0
        self.vlm_clips = 0

    def stats(self) -> dict:
        return {"pose_clips": self.pose_clips, "vlm_clips": self.vlm_clips,
                "vlm": self.vlm_status, "vlm_error": self.vlm_error}

    def _get_vlm(self):
        if self._vlm is not None:
            return self._vlm
        if self._vlm_factory is None:
            return None
        if self.vlm_status == "failed" and \
                self._clock() - self._vlm_failed_at < RETRY_AFTER_FAILURE_S:
            return None
        self.vlm_status = "loading"
        try:
            self._vlm = self._vlm_factory()
            self.vlm_status, self.vlm_error = "ready", None
        except Exception as exc:  # no weights / no memory / missing libs
            self.vlm_status = "failed"
            self.vlm_error = f"{type(exc).__name__}: {exc}"[:300]
            self._vlm_failed_at = self._clock()
        return self._vlm

    def _apply_floor_logic(self, obs: dict) -> dict:
        """Decide on_floor from what has happened across clips, not one posture."""
        if not obs.get("person_present"):
            return obs
        posture, hip, now = obs.get("posture"), obs.get("_hip_y"), self._clock()
        if posture in UPRIGHT_POSTURES:
            self._down = self._rest_confirmed = False
            if hip is not None:
                self._upright_hip, self._upright_at = hip, now
        elif posture == "lying":
            if obs.get("on_floor"):
                self._down = True
            elif (not self._down and hip is not None and self._upright_hip is not None
                  and now - self._upright_at <= CROSS_CLIP_WINDOW_S
                  and hip - self._upright_hip >= SUDDEN_DROP):
                # Upright in the last clip, much lower and lying in this one: the
                # fall happened in the gap between clips.
                obs = {**obs, "sudden_descent": True}
                self._down = True
            if self._down:
                obs = {**obs, "on_floor": True}
        return obs

    def _vlm_due(self, obs: dict, left_view: bool) -> bool:
        since = self._clock() - self._last_vlm
        quiet_rest = self._rest_confirmed and not (
            obs.get("fall_in_progress") or obs.get("sudden_descent")
            or obs.get("on_floor") or obs.get("unsteady_or_swaying"))
        if left_view or (is_odd(obs) and not quiet_rest):
            return since >= self.odd_recheck_s
        moving = obs.get("person_present") and obs.get("motion") in ("active", "slow")
        if moving or scene_has_hazard(self._scene):
            return since >= min(self.vlm_active_interval_s, self.vlm_interval_s)
        return since >= self.vlm_interval_s

    def observe(self, frames, fps: float = 2.0) -> dict:
        pose_obs = self._apply_floor_logic(self._pose.observe(frames, fps=fps))
        self.pose_clips += 1
        present = bool(pose_obs.get("person_present"))
        left_view = self._was_present and not present
        self._was_present = present

        if self._vlm_due(pose_obs, left_view):
            vlm = self._get_vlm()
            if vlm is not None:
                try:
                    vlm_obs = vlm.observe(frames, fps=fps)
                except Exception as exc:
                    self.vlm_status = "failed"
                    self.vlm_error = f"{type(exc).__name__}: {exc}"[:300]
                    self._vlm_failed_at = self._clock()
                    self._vlm = None
                else:
                    self._last_vlm = self._clock()
                    if vlm_obs.get("_parse_failed"):
                        # Not a reading: defaults here would look like "tap off,
                        # door closed" and reset the hazard timers.
                        self.vlm_error = "vision model reply could not be read"
                    else:
                        self.vlm_clips += 1
                        self.vlm_error = None
                        self._scene = {k: vlm_obs.get(k, EMPTY_OBSERVATION[k]) for k in CARRIED}
                        self._down = bool(vlm_obs.get("on_floor"))
                        self._rest_confirmed = (
                            vlm_obs.get("posture") == "lying" and not vlm_obs.get("on_floor")
                            and not vlm_obs.get("fall_in_progress"))
                        vlm_obs["_source"] = "vlm"
                        return vlm_obs  # authoritative when it ran

        # Pose-only clip: keep the last known appliance/water/door state.
        return {**pose_obs, **self._scene}
