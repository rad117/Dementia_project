import logging

import pytest

from monitoring import service as service_module
from monitoring.service import build_default_observer, get_service, live_camera_support
from monitoring.settings import env_float


@pytest.mark.parametrize("raw", ["abc", "", "-5", "0", "inf", "nan"])
def test_bad_numbers_fall_back_to_the_default(raw):
    assert env_float("X", 60.0, env={"X": raw}) == 60.0


def test_a_good_number_is_used():
    assert env_float("X", 60.0, env={"X": "12.5"}) == 12.5
    assert env_float("X", 60.0, env={}) == 60.0


def test_bad_number_is_logged(caplog):
    with caplog.at_level(logging.WARNING):
        env_float("MONITORING_HEARTBEAT_S", 60.0, env={"MONITORING_HEARTBEAT_S": "soon"})
    assert "MONITORING_HEARTBEAT_S" in caplog.text


def test_malformed_heartbeat_does_not_stop_the_service(monkeypatch):
    monkeypatch.setenv("MONITORING_HEARTBEAT_S", "soon")
    assert get_service()._gate.heartbeat_s == 60.0


def _packages(monkeypatch, *present):
    monkeypatch.setattr(service_module, "_has", lambda m: m in present)


def test_missing_pose_model_file_means_not_available(monkeypatch, tmp_path):
    _packages(monkeypatch, "numpy", "PIL", "mediapipe")
    monkeypatch.setenv("MONITORING_POSE_MODEL", str(tmp_path / "absent.task"))
    s = live_camera_support()
    assert s["available"] is False and s["pose"] is False
    assert "download_pose_model" in s["missing"][0]


def test_pose_model_present_means_available_without_torch(monkeypatch, tmp_path):
    model = tmp_path / "pose.task"
    model.write_bytes(b"x")
    _packages(monkeypatch, "numpy", "PIL", "mediapipe")
    monkeypatch.setenv("MONITORING_POSE_MODEL", str(model))
    s = live_camera_support()
    assert s == {"available": True, "missing": [], "pose": True, "vlm": False}


def test_nothing_installed_points_at_the_light_install(monkeypatch):
    _packages(monkeypatch, "numpy", "PIL")
    assert live_camera_support() == {"available": False, "missing": ["mediapipe"],
                                     "pose": False, "vlm": False}


def test_vlm_off_with_no_pose_is_unavailable_and_never_loads_the_model(monkeypatch):
    _packages(monkeypatch, "numpy", "PIL", "torch", "transformers")
    monkeypatch.setenv("MONITORING_VLM", "0")
    assert live_camera_support()["available"] is False
    with pytest.raises(RuntimeError, match="unavailable"):
        build_default_observer()


def test_vlm_is_not_used_on_a_cpu_unless_forced(monkeypatch):
    _packages(monkeypatch, "numpy", "PIL", "torch", "transformers")
    monkeypatch.delenv("MONITORING_VLM", raising=False)
    monkeypatch.setattr(service_module, "_has_accelerator", lambda: False)
    assert live_camera_support()["vlm"] is False
    monkeypatch.setenv("MONITORING_VLM", "1")
    assert live_camera_support()["vlm"] is True


def test_vlm_is_used_automatically_with_a_gpu(monkeypatch):
    _packages(monkeypatch, "numpy", "PIL", "torch", "transformers")
    monkeypatch.delenv("MONITORING_VLM", raising=False)
    monkeypatch.setattr(service_module, "_has_accelerator", lambda: True)
    assert live_camera_support()["vlm"] is True


def test_cpu_pose_install_does_not_pull_in_the_vision_stack():
    from pathlib import Path
    root = Path(service_module.__file__).parent
    assert "torch" not in (root / "requirements.txt").read_text().replace("requirements-vision", "")
    assert "torch" in (root / "requirements-vision.txt").read_text()
