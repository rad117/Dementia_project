import io

import pytest
from fastapi.testclient import TestClient

import backend.db as db_module
import backend.routes.assessments as assessments_module
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    # Route handlers call db.* without an explicit db_path, so they always
    # hit the module-level default -- point that at a throwaway file per
    # test instead of the real dev DB.
    test_db_path = tmp_path / "test_assessments.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    db_module.init_db(test_db_path)


@pytest.fixture(autouse=True)
def _stub_predict(monkeypatch):
    """Decouples these contract tests from needing a trained model artifact
    on disk -- they test the HTTP/persistence contract, not the ML model."""

    def _fake_predict(audio_bytes, *, task_id, language):
        return {
            "risk_score": 0.37,
            "speech_features": {"duration_seconds": 42.0},
            "linguistic_features": {},
            "model_version": "stub-v0",
            "needs_clinician_review": False,
        }

    monkeypatch.setattr(assessments_module, "predict", _fake_predict)


def _create_assessment():
    return client.post(
        "/assessments",
        json={"patientId": "patient-1", "language": "en", "taskId": "cookie-theft"},
    )


def test_create_assessment_returns_id_and_pending_status():
    response = _create_assessment()

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["status"] == "pending_recording"


def test_full_create_upload_results_flow():
    assessment_id = _create_assessment().json()["id"]

    upload_response = client.post(
        f"/assessments/{assessment_id}/audio",
        files={"audio": ("recording.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json() == {"id": assessment_id, "status": "complete"}

    results_response = client.get(f"/assessments/{assessment_id}/results")
    assert results_response.status_code == 200
    body = results_response.json()
    assert body["assessment_id"] == assessment_id
    assert body["language"] == "en"
    assert body["risk_score"] == 0.37
    assert body["speech_features"] == {"duration_seconds": 42.0}
    assert body["linguistic_features"] == {}
    assert body["model_version"] == "stub-v0"
    assert body["needs_clinician_review"] is False


def test_upload_audio_for_unknown_assessment_returns_404():
    response = client.post(
        "/assessments/does-not-exist/audio",
        files={"audio": ("recording.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
    )
    assert response.status_code == 404


def test_get_results_for_unknown_assessment_returns_404():
    response = client.get("/assessments/does-not-exist/results")
    assert response.status_code == 404


def test_get_results_before_audio_uploaded_returns_409():
    assessment_id = _create_assessment().json()["id"]

    response = client.get(f"/assessments/{assessment_id}/results")

    assert response.status_code == 409


def test_upload_audio_maps_audio_processing_error_to_422(monkeypatch):
    from ml.features.acoustic import AudioProcessingError

    def _raise_audio_error(audio_bytes, *, task_id, language):
        raise AudioProcessingError("corrupt audio")

    monkeypatch.setattr(assessments_module, "predict", _raise_audio_error)
    assessment_id = _create_assessment().json()["id"]

    response = client.post(
        f"/assessments/{assessment_id}/audio",
        files={"audio": ("recording.webm", io.BytesIO(b"garbage"), "audio/webm")},
    )

    assert response.status_code == 422
