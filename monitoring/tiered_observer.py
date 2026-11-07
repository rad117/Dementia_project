"""Tiered observer: cheap pose model first, vision model only when it matters.

    every clip ........ PoseObserver (CPU, free): person? posture? fall?
    only if needed .... VLM (GPU, expensive): confirm a fall, read appliances

The VLM is called when the pose tier sees something odd (fall, lying down,
unsteady), and otherwise once every ``vlm_interval_s`` to re-read things a pose
model cannot see (stove, tap, door). In between, pose-only observations carry
the last VLM reading of those things forward, so CareState's timers (stove on
for N minutes, tap running...) keep counting instead of being reset.

If the VLM is missing or fails, pose-only monitoring carries on: falls are
still detected, appliance checks simply stop. That is the resilience story.
"""

import time

from monitoring.nurse_observer import EMPTY_OBSERVATION

# Fields only the VLM can fill; carried forward between VLM looks.
CARRIED = ("appliances", "water_running", "door_open", "location")
RETRY_AFTER_FAILURE_S = 300


def is_odd(obs: dict) -> bool:
    return bool(
        obs.get("fall_in_progress") or obs.get("sudden_descent") or obs.get("on_floor")
        or obs.get("unsteady_or_swaying") or obs.get("posture") in ("lying", "bent_over")
    )


class TieredObserver:
    def __init__(self, pose, vlm_factory=None, vlm_interval_s: float = 600.0,
                 odd_recheck_s: float = 30.0, clock=time.monotonic):
        self._pose = pose
        self._vlm_factory = vlm_factory
        self._vlm = None
        self._vlm_failed_at = float("-inf")
        self.vlm_status = "disabled" if vlm_factory is None else "not_loaded"
        self.vlm_error: str | None = None
        self.vlm_interval_s = vlm_interval_s
        self.odd_recheck_s = odd_recheck_s
        self._clock = clock
        self._last_vlm = float("-inf")
        self._scene = {k: EMPTY_OBSERVATION[k] for k in CARRIED}
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

    def _vlm_due(self, pose_obs: dict) -> bool:
        since = self._clock() - self._last_vlm
        if is_odd(pose_obs):
            return since >= self.odd_recheck_s
        return since >= self.vlm_interval_s

    def observe(self, frames, fps: float = 2.0) -> dict:
        pose_obs = self._pose.observe(frames, fps=fps)
        self.pose_clips += 1

        if self._vlm_due(pose_obs):
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
                    self.vlm_clips += 1
                    self._scene = {k: vlm_obs.get(k, EMPTY_OBSERVATION[k]) for k in CARRIED}
                    vlm_obs["_source"] = "vlm"
                    return vlm_obs  # authoritative when it ran

        # Pose-only clip: keep the last known appliance/water/door state.
        return {**pose_obs, **self._scene}
