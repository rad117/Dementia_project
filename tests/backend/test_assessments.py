import io

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _post_assessment():
    audio_bytes = io.BytesIO(b"fake-audio-bytes")
    return client.post(
        "/api/assessments",
        files={"audio": ("sample.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "task_id": "cookie-theft"},
    )


def test_create_assessment_returns_mock_result():
    response = _post_assessment()

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["model_version"] == "mock-0.0"
    assert "risk_score" in body
    assert "speech_features" in body
    assert "linguistic_features" in body
    assert "needs_clinician_review" in body


def test_create_assessment_ids_are_unique_per_call():
    first_id = _post_assessment().json()["assessment_id"]
    second_id = _post_assessment().json()["assessment_id"]

    assert first_id != second_id
