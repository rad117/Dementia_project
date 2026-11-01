import io
import time

import pytest

from monitoring import service as service_module
from monitoring import store
from monitoring.service import DEMO_TIMELINE, MonitoringService, get_service


def test_ingest_persists_observation_and_alerts():
    svc = get_service()
    alerts = svc.ingest_observation(
        {"person_present": True, "fall_in_progress": True}, patient_id="p1"
    )
    assert [a["kind"] for a in alerts] == ["fall_event"]
    saved = store.list_alerts(patient_id="p1")
    assert len(saved) == 1 and saved[0]["level"] == "CRITICAL"
    assert store.last_observation()["observation"]["fall_in_progress"] is True


def test_ingest_ignores_private_keys_in_observation():
    get_service().ingest_observation({"person_present": False, "_raw": "model text"})
    assert "_raw" not in store.last_observation()["observation"]


def test_demo_timeline_produces_stove_and_fall_alerts_without_touching_live_state():
    svc = get_service()
    alerts = svc.run_demo(patient_id="p1")
    kinds = {a["kind"] for a in alerts}
    assert "unattended_heat_stove" in kinds
    assert "fall_event" in kinds and "fall_motionless" in kinds
    assert all(r["source"] == "demo" for r in store.list_alerts())
    assert svc.status()["state"]["heat_on"] == {}
    assert len(DEMO_TIMELINE) >= 5


def test_demo_is_identical_at_any_time_of_day():
    kinds = [a["kind"] for a in get_service().run_demo()]
    assert "night_activity" not in kinds
    assert kinds == [
        "unattended_heat_stove", "prolonged_absence", "fall_event", "unsteady", "fall_motionless",
    ]


def test_demo_rerun_replaces_instead_of_duplicating():
    svc = get_service()
    first = len(svc.run_demo())
    second = len(svc.run_demo())
    assert first == second == len(store.list_alerts(limit=200))


def test_clear_source_removes_only_that_source():
    svc = get_service()
    svc.run_demo()
    svc.ingest_observation({"person_present": True, "fall_in_progress": True})
    store.clear_source("demo")
    assert {r["source"] for r in store.list_alerts()} == {"live"}


def test_add_frame_reports_unavailable_when_camera_stack_missing(monkeypatch):
    monkeypatch.setattr(
        service_module, "live_camera_support",
        lambda: {"available": False, "missing": ["torch"]},
    )
    assert get_service().add_frame(b"anything") == {"status": "unavailable", "missing": ["torch"]}


def test_observer_load_failure_is_contained(monkeypatch):
    pytest.importorskip("PIL")
    from PIL import Image

    monkeypatch.setattr(
        service_module, "live_camera_support", lambda: {"available": True, "missing": []}
    )

    def boom():
        raise RuntimeError("no weights")

    svc = MonitoringService(observer_factory=boom, clip_len=2, gap_s=0)
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, "JPEG")
    for _ in range(2):
        assert svc.add_frame(buf.getvalue())["status"] == "ok"
    for _ in range(50):
        if not svc._busy:
            break
        time.sleep(0.05)
    status = svc.status()["live_camera"]
    assert status["observer"] == "failed"
    assert "no weights" in status["observer_error"]


def test_live_frames_flow_through_a_fake_observer(monkeypatch):
    pytest.importorskip("PIL")
    from PIL import Image

    monkeypatch.setattr(
        service_module, "live_camera_support", lambda: {"available": True, "missing": []}
    )

    class FakeObserver:
        def observe(self, frames, fps):
            assert len(frames) == 2
            return {"person_present": True, "fall_in_progress": True, "_raw": "x"}

    svc = MonitoringService(observer_factory=FakeObserver, clip_len=2, gap_s=0)
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, "JPEG")
    for _ in range(2):
        svc.add_frame(buf.getvalue())
    for _ in range(50):
        if svc.clips_analysed:
            break
        time.sleep(0.05)
    assert svc.clips_analysed == 1
    assert store.list_alerts()[0]["kind"] == "fall_event"


def test_add_frame_rejects_garbage_bytes(monkeypatch):
    pytest.importorskip("PIL")
    monkeypatch.setattr(
        service_module, "live_camera_support", lambda: {"available": True, "missing": []}
    )
    with pytest.raises(ValueError):
        get_service().add_frame(b"not an image")
