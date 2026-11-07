"""Tier-1 motion gate: decide cheaply whether a frame is worth analysing.

A home camera sees "nothing changed" almost all day. Sending every clip to a
vision model costs thousands of calls per camera per day, so the service first
asks this gate whether the scene moved. Pure numpy; runs on any CPU in
microseconds.

IMPORTANT: no motion does NOT mean nothing to check. A person lying still on
the floor, or a stove left on in an empty room, produce no motion at all. So
the gate also reports a periodic "heartbeat": after ``heartbeat_s`` seconds of
stillness it lets one clip through anyway, so static hazards are still seen
(far less often than every few seconds).
"""

import time

import numpy as np

# Frames are shrunk to a tiny grayscale grid before comparing. This ignores
# sensor noise and makes the check independent of camera resolution.
GRID = (32, 24)  # width, height


def _to_grid(frame: np.ndarray) -> np.ndarray:
    """RGB/gray uint8 array of any size -> float32 (24, 32) grayscale grid."""
    arr = np.asarray(frame)
    if arr.ndim == 3:
        arr = arr[..., :3].mean(axis=2)
    h, w = arr.shape
    gw, gh = GRID
    # Block-average onto the grid (crop the remainder so blocks are equal).
    bh, bw = max(h // gh, 1), max(w // gw, 1)
    arr = arr[: bh * gh, : bw * gw]
    return arr.reshape(gh, bh, gw, bw).mean(axis=(1, 3)).astype(np.float32)


class MotionGate:
    def __init__(self, threshold: float = 4.0, heartbeat_s: float = 300.0,
                 clock=time.monotonic):
        """
        threshold:   mean absolute grey-level change (0-255) that counts as motion.
        heartbeat_s: let a clip through after this long without motion.
        """
        self.threshold = threshold
        self.heartbeat_s = heartbeat_s
        self._clock = clock
        self._prev: np.ndarray | None = None
        self._last_pass = float("-inf")
        self.last_score = 0.0

    def update(self, frame: np.ndarray) -> bool:
        """Feed one frame. True if analysis is warranted (motion or heartbeat)."""
        grid = _to_grid(frame)
        now = self._clock()
        if self._prev is None or self._prev.shape != grid.shape:
            self._prev = grid
            self._last_pass = now
            self.last_score = 0.0
            return True  # first frame: always look once
        self.last_score = float(np.abs(grid - self._prev).mean())
        self._prev = grid
        if self.last_score >= self.threshold:
            self._last_pass = now
            return True
        if now - self._last_pass >= self.heartbeat_s:
            self._last_pass = now
            return True
        return False
