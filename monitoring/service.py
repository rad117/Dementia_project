"""Safety-monitoring service: observations in, risk alerts out.

This is the in-process replacement for the senior's Flask `nurse_server.py`.
The data flow is unchanged:

    camera frames -> clip buffer -> NurseObserver (VLM, structured observation)
                                          |
                                    CareState (temporal rules)
                                          |
                                     risk alerts -> SQLite -> clinician dashboard

Two ways in:

* ``ingest_observation`` takes an already-structured observation (the schema in
  nurse_observer.py). It needs no camera and no ML libraries, so the rules
  engine, API and dashboard are fully usable and testable on any machine.
* ``add_frame`` takes camera JPEGs. It needs the vision stack (see
  ``live_camera_support``). If that stack is missing, or the model fails to
  load, the service reports itself as unavailable -- it never raises into the
  rest of the application.
"""

import importlib.util
import io
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from monitoring import store
from monitoring.care_state import CareState
from monitoring.nurse_observer import EMPTY_OBSERVATION

LIVE_CAMERA_DEPS = ("numpy", "PIL", "torch", "transformers")
MAX_FRAME_BYTES = 10 * 1024 * 1024
MAX_FRAME_WIDTH = 640
OBSERVER_RETRY_S = 300


def live_camera_support() -> dict:
    """Which optional packages the live camera path needs, and which are missing."""
    missing = [m for m in LIVE_CAMERA_DEPS if importlib.util.find_spec(m) is None]
    return {"available": not missing, "missing": missing}


# A short scripted incident: someone cooks, walks away from a lit stove, then
# falls. Used by the dashboard's "run demo" button and by tests. Offsets are
# seconds from the start; thresholds come from CareState.demo().
_P = {"person_present": True, "posture": "standing", "motion": "active"}
_STOVE_ON = [{"name": "stove", "state": "on"}]
DEMO_TIMELINE: list[tuple[int, dict]] = [
    (0, {**_P, "location": "at the kitchen counter", "activity": "stirring a pot",
         "appliances": _STOVE_ON}),
    (10, {**_P, "location": "at the kitchen counter", "activity": "stirring a pot",
          "appliances": _STOVE_ON}),
    (25, {"person_present": False, "appliances": _STOVE_ON}),
    (45, {"person_present": False, "appliances": _STOVE_ON}),
    (55, {**_P, "location": "hallway", "unsteady_or_swaying": True,
          "fall_in_progress": True, "sudden_descent": True}),
    (60, {"person_present": True, "posture": "lying", "on_floor": True,
          "motion": "still", "location": "hallway"}),
    (70, {"person_present": True, "posture": "lying", "on_floor": True,
          "motion": "still", "location": "hallway"}),
]

_LYING = {"person_present": True, "posture": "lying", "on_floor": True, "motion": "still"}
_WALKING = {"person_present": True, "posture": "standing", "motion": "active"}

# Named incidents the clinician can replay for a chosen patient. Each one is a
# sequence of structured observations -- exactly what the vision model emits --
# fed through the real CareState rules (demo thresholds), so the alerts are
# produced by production logic, not hard-coded. ``hour`` is the rules clock,
# so night-time rules behave the same whenever the demo is run.
DEFAULT_SCENARIO = "kitchen_fall"
SCENARIOS: dict[str, dict] = {
    "kitchen_fall": {
        "title": "Stove left on, then a fall",
        "description": "Cooking, walks away from a lit stove, then falls in the hallway.",
        "hour": 14,
        "timeline": DEMO_TIMELINE,
    },
    "bathroom_fall": {
        "title": "Fall in the bathroom",
        "description": "Becomes unsteady at the sink, falls and stays on the floor.",
        "hour": 10,
        "timeline": [
            (0, {**_P, "location": "bathroom sink", "activity": "brushing teeth"}),
            (5, {**_P, "location": "bathroom sink", "unsteady_or_swaying": True}),
            (8, {**_P, "location": "bathroom", "fall_in_progress": True, "sudden_descent": True}),
            (10, {**_LYING, "location": "bathroom floor"}),
            (18, {**_LYING, "location": "bathroom floor"}),
        ],
    },
    "night_wandering": {
        "title": "Night-time wandering",
        "description": "Up at 2 a.m., opens the front door and leaves the monitored area.",
        "hour": 2,
        "timeline": [
            (0, {**_WALKING, "location": "bedroom doorway", "activity": "walking"}),
            (10, {**_WALKING, "location": "hallway", "activity": "walking"}),
            (20, {**_WALKING, "location": "front door", "activity": "opening the door",
                  "door_open": True}),
            (30, {"door_open": True}),
            (50, {"door_open": True}),
        ],
    },
    "tap_running": {
        "title": "Tap left running",
        "description": "Fills a glass at the sink and walks away with the tap on.",
        "hour": 11,
        "timeline": [
            (0, {**_P, "location": "kitchen sink", "activity": "filling a glass",
                 "water_running": True}),
            (8, {"water_running": True}),
            (30, {"water_running": True}),
        ],
    },
    "repeated_task": {
        "title": "Repeating an unfinished task",
        "description": "Keeps going back to search for the same thing without finishing.",
        "hour": 16,
        "timeline": [
            (0, {**_P, "location": "living room", "activity": "searching for keys"}),
            (12, {**_P, "location": "hallway", "activity": "searching for keys"}),
            (24, {**_P, "location": "living room", "activity": "searching for keys"}),
            (36, {**_P, "location": "living room", "activity": "searching for keys"}),
        ],
    },
}


def list_scenarios() -> list[dict]:
    return [{"id": k, "title": v["title"], "description": v["description"]}
            for k, v in SCENARIOS.items()]


class MonitoringService:
    def __init__(self, care_state: CareState | None = None, observer_factory=None,
                 clip_len: int = 8, fps: float = 2.0, gap_s: float = 6.0):
        self._state = care_state or CareState()
        self._state_lock = threading.Lock()
        self._observer_factory = observer_factory
        self._observer = None
        self._observer_status = "not_loaded"      # not_loaded|loading|ready|failed
        self._observer_error: str | None = None
        self._observer_failed_at = 0.0

        self.clip_len = clip_len
        self.fps = fps
        self.gap_s = gap_s
        self._buffer: deque = deque(maxlen=clip_len)
        self._buffer_lock = threading.Lock()
        self._busy = False
        self._last_run = 0.0

        self.frames_received = 0
        self.clips_analysed = 0
        self.last_error: str | None = None

    # ------------------------------------------------------------------
    # structured observations (no camera / ML needed)

    def ingest_observation(self, obs: dict, *, patient_id: str | None = None,
                           now: datetime | None = None, source: str = "live") -> list[dict]:
        """Run one observation through the rules engine; persist; return new alerts."""
        now = now or datetime.now()
        obs = {**EMPTY_OBSERVATION, **{k: v for k, v in obs.items() if not k.startswith("_")}}
        with self._state_lock:
            events = self._state.update(obs, now=now)
        alerts = []
        for e in events:
            e.at = now.isoformat(timespec="seconds")
            alerts.append(e.to_dict())
        store.save_observation(obs, at=now, patient_id=patient_id, source=source)
        store.save_alerts(alerts, patient_id=patient_id, source=source)
        return alerts

    # ------------------------------------------------------------------
    # live camera frames

    def add_frame(self, jpeg: bytes, *, patient_id: str | None = None) -> dict:
        support = live_camera_support()
        if not support["available"]:
            return {"status": "unavailable", "missing": support["missing"]}
        if len(jpeg) > MAX_FRAME_BYTES:
            raise ValueError("frame too large")

        import numpy as np
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(jpeg)).convert("RGB")
        except Exception as exc:
            raise ValueError("frame is not a readable image") from exc
        if img.width > MAX_FRAME_WIDTH:
            img = img.resize((MAX_FRAME_WIDTH, round(img.height * MAX_FRAME_WIDTH / img.width)))
        frame = np.asarray(img)

        with self._buffer_lock:
            self._buffer.append(frame)
            self.frames_received += 1
            ready = len(self._buffer) == self.clip_len
            clip = list(self._buffer) if ready else None
            start = (
                ready and not self._busy
                and time.time() - self._last_run >= self.gap_s
            )
            if start:
                self._busy = True

        if start:
            threading.Thread(
                target=self._analyse, args=(clip, patient_id), daemon=True
            ).start()
        return {"status": "ok", **self._counters()}

    def _ensure_observer(self):
        if self._observer is not None:
            return self._observer
        if self._observer_status == "failed" and \
                time.time() - self._observer_failed_at < OBSERVER_RETRY_S:
            return None
        self._observer_status = "loading"
        try:
            if self._observer_factory is None:
                from monitoring.nurse_observer import NurseObserver
                self._observer = NurseObserver()
            else:
                self._observer = self._observer_factory()
            self._observer_status = "ready"
            self._observer_error = None
        except Exception as exc:  # model download / out of memory / no weights
            self._observer_status = "failed"
            self._observer_error = f"{type(exc).__name__}: {exc}"[:300]
            self._observer_failed_at = time.time()
        return self._observer

    def _analyse(self, clip, patient_id):
        try:
            observer = self._ensure_observer()
            if observer is None:
                return
            obs = observer.observe(clip, fps=self.fps)
            self.ingest_observation(obs, patient_id=patient_id)
            self.clips_analysed += 1
            self.last_error = None
        except Exception as exc:  # never let the worker thread take the app down
            self.last_error = f"{type(exc).__name__}: {exc}"[:300]
        finally:
            self._last_run = time.time()
            self._busy = False

    # ------------------------------------------------------------------

    def _counters(self) -> dict:
        return {"frames": self.frames_received, "clips": self.clips_analysed,
                "observer": self._observer_status}

    def status(self) -> dict:
        support = live_camera_support()
        with self._state_lock:
            state = self._state.status()
        return {
            "live_camera": {
                **support,
                "observer": self._observer_status,
                "observer_error": self._observer_error,
                "last_error": self.last_error,
            },
            "counters": self._counters(),
            "state": state,
        }

    # ------------------------------------------------------------------
    # scripted demo

    def run_demo(self, *, patient_id: str | None = None,
                 scenario: str = DEFAULT_SCENARIO) -> list[dict]:
        """Replay a named scenario through a throwaway CareState.

        Uses its own state (short demo thresholds) so it never disturbs live
        monitoring, and tags everything source='demo' so it can be cleared.
        Re-running a scenario for the same patient replaces its earlier alerts
        instead of duplicating them; other scenarios' alerts are kept.
        Raises KeyError for an unknown scenario.
        """
        spec = SCENARIOS[scenario]
        timeline = spec["timeline"]
        store.clear_demo_scenario(scenario, patient_id)
        demo_state = CareState.demo()
        # Rules are evaluated on a fixed clock per scenario (mid-afternoon for
        # most, 2 a.m. for night wandering) so the demo is identical at any
        # hour; alerts are stamped with the real wall-clock time they stand for.
        rules_base = datetime.now().replace(hour=spec["hour"], minute=0, second=0, microsecond=0)
        shown_base = datetime.now() - timedelta(seconds=timeline[-1][0] + 5)
        alerts: list[dict] = []
        for offset, partial in timeline:
            obs = {**EMPTY_OBSERVATION, **partial}
            events = demo_state.update(obs, now=rules_base + timedelta(seconds=offset))
            for e in events:
                e.at = (shown_base + timedelta(seconds=offset)).isoformat(timespec="seconds")
                alerts.append(e.to_dict())
        store.save_alerts(alerts, patient_id=patient_id, source="demo", scenario=scenario)
        return alerts


_service: MonitoringService | None = None
_service_lock = threading.Lock()


def get_service() -> MonitoringService:
    global _service
    with _service_lock:
        if _service is None:
            demo = os.environ.get("MONITORING_DEMO") == "1"
            _service = MonitoringService(care_state=CareState.demo() if demo else None)
        return _service


def reset_service() -> None:
    """Drop the singleton (tests)."""
    global _service
    with _service_lock:
        _service = None
