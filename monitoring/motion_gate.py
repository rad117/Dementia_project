"""Tier-1 motion gate: decide cheaply whether a frame is worth analysing.

A home camera sees "nothing changed" almost all day, so the service first asks
this gate whether the scene moved. Pure numpy; runs on any CPU in microseconds.

Three things count as motion, compared against the frame at the last pass (not
just the previous frame), so slow movement adds up instead of being forgotten:

* the whole picture changed on average (someone walks through);
* a few grid cells changed a lot (a small or distant person moved);
* the periodic heartbeat came due.

IMPORTANT: no motion does NOT mean nothing to check. A person lying still on
the floor, or a stove left on in an empty room, produce no motion at all. So
after ``heartbeat_s`` seconds of stillness one clip is let through anyway. The
pose tier is free to run, so this is short; the vision model has its own schedule.
"""

import math
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
    gw, gh = GRID
    # Frames smaller than the grid are enlarged by repeating pixels.
    arr = np.repeat(arr, math.ceil(gh / arr.shape[0]), axis=0)
    arr = np.repeat(arr, math.ceil(gw / arr.shape[1]), axis=1)
    h, w = arr.shape
    # Block-average onto the grid (crop the remainder so blocks are equal).
    bh, bw = h // gh, w // gw
    arr = arr[: bh * gh, : bw * gw]
    return arr.reshape(gh, bh, gw, bw).mean(axis=(1, 3)).astype(np.float32)


class MotionGate:
    def __init__(self, threshold: float = 4.0, heartbeat_s: float = 60.0,
                 cell_threshold: float = 10.0, min_cells: int = 6,
                 clock=time.monotonic):
        """
        threshold:      mean absolute grey-level change (0-255) over the whole frame.
        heartbeat_s:    let a clip through after this long without motion.
        cell_threshold: grey-level change that marks one grid cell as changed.
        min_cells:      this many changed cells count as motion (about 1% of the grid).
        """
        self.threshold = threshold
        self.heartbeat_s = heartbeat_s
        self.cell_threshold = cell_threshold
        self.min_cells = min_cells
        self._clock = clock
        self._ref: np.ndarray | None = None
        self._last_pass = float("-inf")
        self.last_score = 0.0

    def update(self, frame: np.ndarray) -> bool:
        """Feed one frame. True if analysis is warranted (motion or heartbeat)."""
        grid = _to_grid(frame)
        now = self._clock()
        if self._ref is None:
            self._ref, self._last_pass, self.last_score = grid, now, 0.0
            return True  # first frame: always look once
        diff = np.abs(grid - self._ref)
        self.last_score = float(diff.mean())
        moved = (self.last_score >= self.threshold
                 or int((diff >= self.cell_threshold).sum()) >= self.min_cells)
        if moved or now - self._last_pass >= self.heartbeat_s:
            self._ref, self._last_pass = grid, now
            return True
        return False
