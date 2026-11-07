"""Tier-2 observer: body pose -> the same structured observation the VLM makes.

Falls, "on the floor" and who-is-present are body-position questions. A small
pose model (MediaPipe) answers them on an ordinary CPU, several times a second,
at no per-call cost, so the large vision model is not needed for them.

``observation_from_poses`` is a pure function over landmark coordinates, so the
classification is unit-tested with synthetic poses and needs no camera.
``PoseObserver`` wraps MediaPipe and feeds it.

What this tier cannot see: whether a stove is on, whether a tap is running,
what the hands are doing. Those fields stay at their defaults here; the
tiered observer asks the vision model for them occasionally.

Camera geometry matters: thresholds assume a roughly side-on / wall-mounted
camera. A ceiling camera would need different angle limits.
"""

import math
import os
import threading
from pathlib import Path

from monitoring.nurse_observer import EMPTY_OBSERVATION

DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "pose_landmarker_lite.task"

# MediaPipe BlazePose landmark indices.
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26

MIN_VISIBILITY = 0.4          # torso points must be at least this visible
LYING_ANGLE = 60.0            # torso this far from vertical (deg) = lying
BENT_ANGLE = 35.0
FALL_ANGLE_JUMP = 40.0        # torso tilts this much between two frames = falling
SUDDEN_DROP = 0.18            # hips move down this much (fraction of frame height)
SHRINK_RATIO = 0.65           # body height falls to this fraction of its clip maximum
ACTIVE_MOTION = 0.04
SLOW_MOTION = 0.01


def _mid(lm, a, b):
    return ((lm[a][0] + lm[b][0]) / 2, (lm[a][1] + lm[b][1]) / 2)


def pose_model_path() -> Path:
    return Path(os.environ.get("MONITORING_POSE_MODEL") or DEFAULT_MODEL_PATH)


def analyse_pose(lm) -> dict | None:
    """One frame's 33 landmarks [(x, y, visibility), ...] -> metrics, or None if unusable."""
    if not lm or len(lm) < 33:
        return None
    torso = (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP)
    if sum(lm[i][2] for i in torso) / len(torso) < MIN_VISIBILITY:
        return None
    sx, sy = _mid(lm, L_SHOULDER, R_SHOULDER)
    hx, hy = _mid(lm, L_HIP, R_HIP)
    dx, dy = sx - hx, sy - hy
    torso_len = math.hypot(dx, dy)
    if torso_len < 1e-4:
        return None
    angle = math.degrees(math.atan2(abs(dx), abs(dy)))   # 0 upright .. 90 horizontal

    visible = [p for p in lm if p[2] >= 0.3]
    ys = [p[1] for p in visible]
    height = (max(ys) - min(ys)) if ys else 0.0

    knees_ok = lm[L_KNEE][2] >= 0.3 and lm[R_KNEE][2] >= 0.3
    thigh_drop = None
    if knees_ok:
        knee_y = (lm[L_KNEE][1] + lm[R_KNEE][1]) / 2
        thigh_drop = (knee_y - hy) / torso_len  # ~0.9-1.1 standing, small when seated

    if angle >= LYING_ANGLE:
        posture = "lying"
    elif angle >= BENT_ANGLE:
        posture = "bent_over"
    elif thigh_drop is not None:
        posture = "sitting" if thigh_drop < 0.45 else "standing"
    else:
        # Upper body only (typical laptop/wall camera): clearly upright, but
        # standing vs sitting cannot be told without the legs.
        posture = "upright"

    return {
        "posture": posture, "angle": angle, "hip_y": hy, "height": height,
        "points": [(lm[i][0], lm[i][1]) for i in torso],
    }


def _displacement(a, b) -> float:
    return sum(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(a["points"], b["points"])) / len(a["points"])


def observation_from_poses(poses: list) -> dict:
    """A clip's per-frame landmark lists (None where no person) -> one observation."""
    metrics = [analyse_pose(p) if p else None for p in poses]
    valid = [m for m in metrics if m]
    obs = dict(EMPTY_OBSERVATION)
    obs["_source"] = "pose"
    if not valid:
        obs["person_present"] = False
        obs["motion"] = "none"
        return obs

    last = valid[-1]
    obs["person_present"] = True
    obs["posture"] = last["posture"]
    obs["_hip_y"] = last["hip_y"]

    steps = list(zip(valid, valid[1:]))
    if steps:
        motion = sum(_displacement(a, b) for a, b in steps) / len(steps)
        obs["motion"] = ("active" if motion >= ACTIVE_MOTION
                         else "slow" if motion >= SLOW_MOTION else "still")
    else:
        obs["motion"] = "unknown"

    # Falling: the torso tips over within a step or two and ends HORIZONTAL.
    # Leaning down to pick something up ends bent, not lying, so it is not a fall.
    obs["fall_in_progress"] = any(
        b["angle"] - a["angle"] >= FALL_ANGLE_JUMP and b["angle"] >= LYING_ANGLE
        for a, b in steps
    )
    # Sudden descent: hips drop sharply, the body gets much shorter in frame, and
    # the person does not end up sitting or upright (sitting down quickly is not a fall).
    if len(valid) >= 2:
        top_hip = min(m["hip_y"] for m in valid[:-1])
        tallest = max(m["height"] for m in valid[:-1])
        obs["sudden_descent"] = bool(
            last["hip_y"] - top_hip >= SUDDEN_DROP
            and tallest > 0 and last["height"] / tallest <= SHRINK_RATIO
            and last["posture"] in ("lying", "bent_over")
        )
    # A pose cannot tell a bed from the floor, so lying alone is not "on the
    # floor". Only a fall or sharp drop seen in this clip makes it so; the tiered
    # observer carries that across clips and also catches drops between clips.
    obs["on_floor"] = last["posture"] == "lying" and bool(
        obs["fall_in_progress"] or obs["sudden_descent"])
    return obs


class PoseObserver:
    """MediaPipe pose landmarker; turns a clip of RGB frames into an observation."""

    def __init__(self, model_path: str | os.PathLike | None = None):
        path = Path(model_path) if model_path else pose_model_path()
        if not path.exists():
            raise FileNotFoundError(
                f"pose model not found at {path}; run scripts/download_pose_model.sh")
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self._mp = mp
        self._landmarker = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(path)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
            ))
        self._lock = threading.Lock()

    def observe(self, frames, fps: float = 2.0) -> dict:
        import numpy as np

        poses = []
        with self._lock:
            for f in frames:
                img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB,
                                     data=np.ascontiguousarray(np.asarray(f, dtype=np.uint8)))
                res = self._landmarker.detect(img)
                if res.pose_landmarks:
                    poses.append([(p.x, p.y, p.visibility) for p in res.pose_landmarks[0]])
                else:
                    poses.append(None)
        return observation_from_poses(poses)
