import io

import numpy as np
from PIL import Image

from monitoring.motion_gate import MotionGate
from monitoring.service import MonitoringService


def _frame(value: int, size=(160, 120)) -> np.ndarray:
    return np.full((size[1], size[0], 3), value, dtype=np.uint8)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_first_frame_always_passes():
    assert MotionGate().update(_frame(100)) is True


def test_still_scene_is_skipped():
    gate = MotionGate()
    gate.update(_frame(100))
    assert all(gate.update(_frame(100)) is False for _ in range(20))


def test_small_sensor_noise_is_not_motion():
    rng = np.random.default_rng(0)
    gate = MotionGate()
    base = _frame(100).astype(int)
    gate.update(base.astype(np.uint8))
    for _ in range(10):
        noisy = np.clip(base + rng.integers(-2, 3, base.shape), 0, 255).astype(np.uint8)
        assert gate.update(noisy) is False


def test_real_change_passes():
    gate = MotionGate()
    gate.update(_frame(100))
    moved = _frame(100)
    moved[:, :80] = 220  # half the picture changes (e.g. a person walks in)
    assert gate.update(moved) is True


def test_heartbeat_lets_static_scene_through_eventually():
    """A person lying still or a stove left on makes no motion -- still check."""
    clock = Clock()
    gate = MotionGate(heartbeat_s=300, clock=clock)
    gate.update(_frame(100))
    clock.t = 299
    assert gate.update(_frame(100)) is False
    clock.t = 301
    assert gate.update(_frame(100)) is True
    clock.t = 302
    assert gate.update(_frame(100)) is False  # timer restarts


def test_resolution_change_does_not_crash():
    gate = MotionGate()
    gate.update(_frame(100, size=(160, 120)))
    # Same scene at a new resolution: compared on the same tiny grid, so no motion.
    assert gate.update(_frame(100, size=(320, 240))) is False
    moved = _frame(100, size=(320, 240))
    moved[:, :160] = 220
    assert gate.update(moved) is True


def _jpeg(value: int) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(_frame(value)).save(buf, "JPEG")
    return buf.getvalue()


def test_service_skips_model_while_scene_is_still(monkeypatch):
    monkeypatch.setattr("monitoring.service.live_camera_support",
                        lambda: {"available": True, "missing": []})
    calls = []

    class FakeObserver:
        def observe(self, clip, fps=2.0):
            calls.append(1)
            return {"person_present": False}

    svc = MonitoringService(observer_factory=FakeObserver, clip_len=2, gap_s=0,
                            motion_gate=MotionGate())
    import time
    for _ in range(12):
        svc.add_frame(_jpeg(100))
        time.sleep(0.02)
    time.sleep(0.3)
    # Only the very first look; the still scene afterwards never wakes the model.
    assert len(calls) == 1


def test_small_distant_movement_passes():
    gate = MotionGate()
    gate.update(_frame(100, size=(640, 480)))
    moved = _frame(100, size=(640, 480))
    moved[100:160, 300:360] = 200    # a small area, far below the whole-frame average
    assert gate.update(moved) is True
    assert gate.last_score < gate.threshold


def test_slow_movement_adds_up_against_the_last_passed_frame():
    gate = MotionGate()
    gate.update(_frame(100))
    assert gate.update(_frame(102)) is False
    assert gate.update(_frame(103)) is False
    assert gate.update(_frame(105)) is True          # no single step reached the threshold


def test_default_heartbeat_is_short():
    assert MotionGate().heartbeat_s == 60


def test_frames_smaller_than_the_grid_do_not_crash():
    gate = MotionGate()
    assert gate.update(np.zeros((6, 8, 3), np.uint8)) is True
    assert gate.update(np.zeros((6, 8, 3), np.uint8)) is False
    assert gate.update(np.zeros((1, 1), np.uint8)) is False
