import io
import time

import numpy as np
from PIL import Image

from monitoring.motion_gate import MotionGate
from monitoring.pose_observer import observation_from_poses
from monitoring.service import MonitoringService
from monitoring.tiered_observer import TieredObserver


def make_pose(kind: str, cx: float = 0.5, hip_y: float = 0.55, vis: float = 0.9):
    """33 synthetic BlazePose landmarks for a stick figure."""
    lm = [(cx, hip_y, vis)] * 33
    lm = list(lm)

    def put(i, x, y):
        lm[i] = (x, y, vis)

    if kind == "standing":
        sh_y, kn_y, ank_y = hip_y - 0.2, hip_y + 0.22, hip_y + 0.42
        for i, dx in ((11, -0.04), (12, 0.04)):
            put(i, cx + dx, sh_y)
        for i, dx in ((23, -0.03), (24, 0.03)):
            put(i, cx + dx, hip_y)
        for i, dx in ((25, -0.03), (26, 0.03)):
            put(i, cx + dx, kn_y)
        for i, dx in ((27, -0.03), (28, 0.03)):
            put(i, cx + dx, ank_y)
        put(0, cx, sh_y - 0.08)
    elif kind == "sitting":
        for i, dx in ((11, -0.04), (12, 0.04)):
            put(i, cx + dx, hip_y - 0.2)
        for i, dx in ((23, -0.03), (24, 0.03)):
            put(i, cx + dx, hip_y)
        for i, dx in ((25, -0.03), (26, 0.03)):
            put(i, cx + 0.15, hip_y + 0.02)   # thighs horizontal
        for i, dx in ((27, -0.03), (28, 0.03)):
            put(i, cx + 0.15, hip_y + 0.22)
    elif kind == "lying":
        for i, dy in ((11, -0.02), (12, 0.02)):
            put(i, cx - 0.2, hip_y + dy)
        for i, dy in ((23, -0.02), (24, 0.02)):
            put(i, cx, hip_y + dy)
        for i, dy in ((25, -0.02), (26, 0.02)):
            put(i, cx + 0.12, hip_y + dy)
        for i, dy in ((27, -0.02), (28, 0.02)):
            put(i, cx + 0.22, hip_y + dy)
        put(0, cx - 0.28, hip_y)
    return lm


def test_no_person_means_not_present():
    obs = observation_from_poses([None, None, None])
    assert obs["person_present"] is False and obs["motion"] == "none"


def test_standing_person_is_normal():
    obs = observation_from_poses([make_pose("standing")] * 4)
    assert obs["person_present"] and obs["posture"] == "standing"
    assert not obs["on_floor"] and not obs["fall_in_progress"] and not obs["sudden_descent"]
    assert obs["motion"] == "still"


def test_sitting_is_not_mistaken_for_lying_or_standing():
    obs = observation_from_poses([make_pose("sitting")] * 3)
    assert obs["posture"] == "sitting" and not obs["on_floor"]


def test_lying_still_alone_is_not_on_the_floor():
    """Could be a bed or a couch: a pose cannot tell."""
    obs = observation_from_poses([make_pose("lying", hip_y=0.85)] * 4)
    assert obs["posture"] == "lying" and obs["on_floor"] is False
    assert obs["fall_in_progress"] is False
    assert obs["motion"] == "still"


def test_standing_to_lying_in_one_clip_is_a_fall():
    clip = [make_pose("standing")] * 3 + [make_pose("lying", hip_y=0.85)] * 2
    obs = observation_from_poses(clip)
    assert obs["fall_in_progress"] is True
    assert obs["sudden_descent"] is True
    assert obs["on_floor"] is True


def test_upper_body_only_is_upright_not_unknown():
    lm = make_pose("standing")
    for i in range(25, 33):                 # legs not visible (laptop camera)
        lm[i] = (lm[i][0], lm[i][1], 0.0)
    obs = observation_from_poses([lm] * 3)
    assert obs["posture"] == "upright" and obs["person_present"]
    assert not obs["on_floor"] and not obs["fall_in_progress"]


def test_leaning_over_to_pick_something_up_is_not_a_fall():
    lean = make_pose("standing")
    for i, dx in ((11, 0.14), (12, 0.22)):  # shoulders forward of hips ~ 45 degrees
        lean[i] = (0.5 + dx, 0.55 - 0.14, 0.9)
    obs = observation_from_poses([make_pose("standing")] * 2 + [lean] * 2)
    assert obs["fall_in_progress"] is False and obs["on_floor"] is False


def test_sitting_down_quickly_is_not_a_fall():
    clip = [make_pose("standing")] * 2 + [make_pose("sitting", hip_y=0.75)] * 3
    obs = observation_from_poses(clip)
    assert obs["sudden_descent"] is False and obs["fall_in_progress"] is False


def test_low_visibility_pose_is_ignored():
    obs = observation_from_poses([make_pose("standing", vis=0.1)] * 3)
    assert obs["person_present"] is False


# ---------------------------------------------------------------- tiering

class FakePose:
    def __init__(self, script):
        self.script, self.i = script, 0

    def observe(self, frames, fps=2.0):
        obs = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return {"person_present": True, "posture": "standing", "on_floor": False,
                "fall_in_progress": False, "sudden_descent": False,
                "unsteady_or_swaying": False, "appliances": [], "water_running": False,
                "door_open": False, "location": "unknown", **obs}


class FakeVlm:
    def __init__(self, reply=None):
        self.calls = 0
        self.reply = reply or {"person_present": True, "posture": "standing",
                               "appliances": [{"name": "stove", "state": "on"}],
                               "water_running": True, "door_open": False,
                               "location": "kitchen"}

    def observe(self, frames, fps=2.0):
        self.calls += 1
        return dict(self.reply)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_calm_clips_do_not_call_the_vlm_between_intervals():
    clock, vlm = Clock(), FakeVlm({"person_present": True, "posture": "standing"})
    t = TieredObserver(FakePose([{}]), vlm_factory=lambda: vlm, vlm_interval_s=600, clock=clock)
    t.observe([1]); assert vlm.calls == 1           # first look reads the scene
    for step in range(1, 50):
        clock.t = step * 6
        t.observe([1])
    assert vlm.calls == 1                            # 5 minutes of calm: no more calls
    clock.t = 700
    t.observe([1]); assert vlm.calls == 2            # interval elapsed: re-read appliances


def test_pose_only_clips_carry_appliance_state_forward():
    clock, vlm = Clock(), FakeVlm()
    t = TieredObserver(FakePose([{}]), vlm_factory=lambda: vlm, clock=clock)
    t.observe([1])
    clock.t = 10
    obs = t.observe([1])
    assert vlm.calls == 1
    assert obs["appliances"] == [{"name": "stove", "state": "on"}]
    assert obs["water_running"] is True              # timers keep counting


def test_fall_calls_vlm_immediately_and_vlm_is_authoritative():
    clock, vlm = Clock(), FakeVlm({"person_present": True, "posture": "standing",
                                   "fall_in_progress": False})
    t = TieredObserver(FakePose([{}, {"fall_in_progress": True, "posture": "lying",
                                      "on_floor": True}]),
                       vlm_factory=lambda: vlm, vlm_interval_s=600, odd_recheck_s=30, clock=clock)
    t.observe([1]); clock.t = 40
    obs = t.observe([1])
    assert vlm.calls == 2 and obs["fall_in_progress"] is False   # VLM judged it a false alarm


def test_falls_still_detected_when_vlm_is_unavailable():
    def boom():
        raise RuntimeError("no weights")

    pose = FakePose([{"fall_in_progress": True, "posture": "lying", "on_floor": True}])
    t = TieredObserver(pose, vlm_factory=boom, clock=Clock())
    obs = t.observe([1])
    assert obs["fall_in_progress"] is True
    assert t.vlm_status == "failed" and "no weights" in t.vlm_error


def test_pose_only_mode_has_no_vlm():
    t = TieredObserver(FakePose([{}]), vlm_factory=None, clock=Clock())
    assert t.observe([1])["person_present"] is True and t.vlm_status == "disabled"


# ----------------------------------------------- gate stays open for hazards

def _jpeg(value):
    buf = io.BytesIO()
    Image.fromarray(np.full((120, 160, 3), value, np.uint8)).save(buf, "JPEG")
    return buf.getvalue()


def test_gate_stays_open_while_a_hazard_is_active(monkeypatch):
    """Someone lying still on the floor makes no motion, but must keep being checked."""
    monkeypatch.setattr("monitoring.service.live_camera_support",
                        lambda: {"available": True, "missing": []})
    calls = []

    class Obs:
        def observe(self, clip, fps=2.0):
            calls.append(1)
            return {"person_present": True, "posture": "lying", "on_floor": True,
                    "motion": "none"}

    svc = MonitoringService(observer_factory=Obs, clip_len=2, gap_s=0, motion_gate=MotionGate())
    for _ in range(40):
        svc.add_frame(_jpeg(100))      # identical frames: zero motion
        time.sleep(0.03)
    time.sleep(0.3)
    assert len(calls) > 3              # kept analysing the still, dangerous scene


# ------------------------------------------------- bed vs floor across clips

def _pose_clip(kind, hip_y):
    return observation_from_poses([make_pose(kind, hip_y=hip_y)] * 4)


class ScriptedPose:
    def __init__(self, clips):
        self.clips, self.i = clips, 0

    def observe(self, frames, fps=2.0):
        clip = self.clips[min(self.i, len(self.clips) - 1)]
        self.i += 1
        return dict(clip)


def test_lying_down_on_a_bed_raises_no_fall_alert():
    from datetime import datetime, timedelta
    from monitoring.care_state import CareState

    clock = Clock()
    t = TieredObserver(ScriptedPose([_pose_clip("sitting", 0.60), _pose_clip("lying", 0.62)]), clock=clock)
    state, start, kinds = CareState(), datetime(2026, 1, 1, 14, 0), set()
    for step in range(12):
        clock.t = step * 6
        obs = {k: v for k, v in t.observe([1]).items() if not k.startswith("_")}
        kinds |= {e.kind for e in state.update(obs, now=start + timedelta(seconds=step * 6))}
    assert not kinds & {"fall", "fall_event", "fall_motionless"}


def test_fall_between_clips_is_caught_and_stays_on_the_floor_until_they_get_up():
    clock = Clock()
    t = TieredObserver(ScriptedPose([_pose_clip("standing", 0.40), _pose_clip("lying", 0.85),
                                     _pose_clip("lying", 0.85), _pose_clip("standing", 0.40),
                                     _pose_clip("lying", 0.42)]), clock=clock)
    t.observe([1]); clock.t = 6
    first = t.observe([1])
    assert first["sudden_descent"] is True and first["on_floor"] is True
    clock.t = 12
    assert t.observe([1])["on_floor"] is True        # still down, no new motion
    clock.t = 18
    assert t.observe([1])["on_floor"] is False       # got up
    clock.t = 60
    assert t.observe([1])["on_floor"] is False       # later rest is not the old fall


def test_old_upright_reading_is_not_compared_across_clips():
    clock = Clock()
    t = TieredObserver(ScriptedPose([_pose_clip("standing", 0.40), _pose_clip("lying", 0.85)]), clock=clock)
    t.observe([1]); clock.t = 300
    assert t.observe([1])["on_floor"] is False


def test_vlm_saying_floor_overrides_and_vlm_saying_bed_stops_repeat_calls():
    clock = Clock()
    vlm = FakeVlm({"person_present": True, "posture": "lying", "on_floor": False, "motion": "still"})
    t = TieredObserver(ScriptedPose([_pose_clip("lying", 0.6)]), vlm_factory=lambda: vlm,
                       vlm_interval_s=600, odd_recheck_s=30, clock=clock)
    t.observe([1])
    for step in range(1, 40):                         # four minutes asleep
        clock.t = step * 6
        t.observe([1])
    assert vlm.calls == 1

    clock2 = Clock()
    vlm2 = FakeVlm({"person_present": True, "posture": "lying", "on_floor": True})
    t2 = TieredObserver(ScriptedPose([_pose_clip("lying", 0.6)]), vlm_factory=lambda: vlm2, clock=clock2)
    t2.observe([1])
    clock2.t = 6
    assert t2.observe([1])["on_floor"] is True        # pose-only clip keeps the VLM's verdict


# ------------------------------------------------------- appliance schedule

def _reading(stove):
    return {"person_present": True, "posture": "standing",
            "appliances": [{"name": "stove", "state": stove}]}


def test_vlm_checks_every_two_minutes_while_someone_is_moving():
    clock, vlm = Clock(), FakeVlm({"person_present": True, "posture": "standing"})
    t = TieredObserver(FakePose([{"motion": "active"}]), vlm_factory=lambda: vlm, clock=clock)
    t.observe([1])
    clock.t = 100; t.observe([1]); assert vlm.calls == 1
    clock.t = 130; t.observe([1]); assert vlm.calls == 2


def test_vlm_keeps_checking_a_flagged_hazard_in_a_calm_scene():
    clock, vlm = Clock(), FakeVlm(_reading("on"))
    t = TieredObserver(FakePose([{}]), vlm_factory=lambda: vlm, clock=clock)
    t.observe([1])
    clock.t = 130; t.observe([1]); assert vlm.calls == 2


def test_vlm_looks_when_the_person_leaves_view():
    """They may have walked away from a lit stove."""
    clock, vlm = Clock(), FakeVlm({"person_present": False})
    t = TieredObserver(FakePose([{}, {"person_present": False}]), vlm_factory=lambda: vlm, clock=clock)
    t.observe([1]); assert vlm.calls == 1
    clock.t = 40
    t.observe([1]); assert vlm.calls == 2


def test_unreadable_vlm_reply_keeps_the_last_hazard_reading():
    from monitoring.nurse_observer import EMPTY_OBSERVATION

    clock = Clock()
    replies = [{"person_present": True, "posture": "standing", "water_running": True, "door_open": True},
               {**EMPTY_OBSERVATION, "_parse_failed": True}]

    class Vlm:
        def observe(self, frames, fps=2.0):
            return dict(replies.pop(0))

    t = TieredObserver(FakePose([{}]), vlm_factory=Vlm, clock=clock)
    t.observe([1])
    clock.t = 130
    obs = t.observe([1])
    assert obs["water_running"] is True and obs["door_open"] is True
    assert obs["person_present"] is True              # the pose reading, not the blank
    assert "could not be read" in t.stats()["vlm_error"]
    assert t.stats()["vlm_clips"] == 1


# ----------------------------------------------------------------- service

def _run_frames(svc, n=4):
    for _ in range(n):
        svc.add_frame(_jpeg(100))
        time.sleep(0.03)
    time.sleep(0.2)


def test_service_ignores_an_unreadable_reply_from_a_lone_vision_model(monkeypatch):
    from monitoring import store
    from monitoring.nurse_observer import EMPTY_OBSERVATION

    monkeypatch.setattr("monitoring.service.live_camera_support",
                        lambda: {"available": True, "missing": []})

    class Obs:
        def observe(self, clip, fps=2.0):
            return {**EMPTY_OBSERVATION, "_parse_failed": True}

    svc = MonitoringService(observer_factory=Obs, clip_len=2, gap_s=0)
    svc._state.update({"person_present": True, "water_running": True})
    _run_frames(svc)
    assert svc._state.water_on_since is not None
    assert store.last_observation() is None
    assert "could not be read" in svc.last_error


def test_gate_stays_open_during_the_fall_followup_window(monkeypatch):
    """Fell, then out of view with nothing moving: fall_then_lost must still fire."""
    from monitoring import store

    monkeypatch.setattr("monitoring.service.live_camera_support",
                        lambda: {"available": True, "missing": []})
    replies = [{"person_present": True, "fall_in_progress": True}]

    class Obs:
        def observe(self, clip, fps=2.0):
            return replies.pop(0) if replies else {"person_present": False}

    svc = MonitoringService(observer_factory=Obs, clip_len=2, gap_s=0, motion_gate=MotionGate())
    for _ in range(30):
        svc.add_frame(_jpeg(100))
        time.sleep(0.02)
    time.sleep(0.2)
    assert "fall_then_lost" in {a["kind"] for a in store.list_alerts()}


def test_a_tiny_frame_is_accepted(monkeypatch):
    monkeypatch.setattr("monitoring.service.live_camera_support",
                        lambda: {"available": True, "missing": []})
    buf = io.BytesIO()
    Image.new("RGB", (8, 6)).save(buf, "JPEG")
    svc = MonitoringService(observer_factory=lambda: None, clip_len=50, motion_gate=MotionGate())
    assert svc.add_frame(buf.getvalue())["status"] == "ok"
