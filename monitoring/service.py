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

    def run_demo(self, *, patient_id: str | None = None) -> list[dict]:
        """Replay DEMO_TIMELINE through a throwaway CareState.

        Uses its own state (short demo thresholds) so it never disturbs live
        monitoring, and tags everything source='demo' so it can be cleared.
        """
        store.clear_source("demo")
        demo_state = CareState.demo()
        # Rules are evaluated at a fixed mid-afternoon time so the night-time
        # rules never fire and the demo is identical at any hour; the alerts
        # are stamped with the real wall-clock time they stand in for.
        rules_base = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        shown_base = datetime.now() - timedelta(seconds=DEMO_TIMELINE[-1][0] + 5)
        alerts: list[dict] = []
        for offset, partial in DEMO_TIMELINE:
            obs = {**EMPTY_OBSERVATION, **partial}
            events = demo_state.update(obs, now=rules_base + timedelta(seconds=offset))
            for e in events:
                e.at = (shown_base + timedelta(seconds=offset)).isoformat(timespec="seconds")
                alerts.append(e.to_dict())
        store.save_alerts(alerts, patient_id=patient_id, source="demo")
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
