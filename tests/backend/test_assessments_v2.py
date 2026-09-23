import io

import pytest
from fastapi.testclient import TestClient

import backend.routes.assessments as assessments_module
from backend.main import app

client = TestClient(app)


def _fake_predict_result(*, risk_score=0.37, needs_review=False, word_count=5, concepts_identified=6.0):
    return {
        "risk_score": risk_score,
        "speech_features": {
            "duration_seconds": 42.0,
            "pause_count": 5.0,
            "total_pause_duration_seconds": 8.0,
            "pause_ratio": 0.19,
            "voiced_rate_per_min": 10.0,
            "longest_pause_seconds": 2.0,
            "first_speech_onset_seconds": 1.0,
            "pitch_mean_hz": 150.0,
            "pitch_std_hz": 20.0,
            "voice_breaks_count": 1.0,
            "energy_rms_mean": 0.05,
            "energy_rms_std": 0.01,
            "jitter_percent": 0.5,
            "shimmer_percent": 3.0,
            "hnr_db": 18.0,
            "spectral_centroid_hz_mean": 1800.0,
            **{f"mfcc_{i}_mean": float(i) for i in range(1, 14)},
            **{f"mfcc_{i}_std": float(i) for i in range(1, 14)},
        },
        "linguistic_features": {
            "transcript_text": "the boy is stealing cookies",
            "word_count": word_count,
            "avg_logprob": -0.3,
            "no_speech_prob": 0.05,
            "detected_language": "en",
            "detected_language_probability": 0.99,
            "type_token_ratio": 1.0,
            "unique_word_count": word_count,
            "filler_word_count": 0.0,
            "words_per_sentence": float(word_count),
            "repeated_word_count": 0.0,
            "generic_substitution_count": 0.0,
            "revision_marker_count": 0.0,
            "incomplete_utterance_count": 0.0,
            "syntactic_complexity_score": 0.0,
            "retrieval_event_count": 0.0,
        },
        "semantic_features": {
            "concept_coverage": concepts_identified / 15,
            "concepts_identified": concepts_identified,
            "concepts_expected": 15.0,
            "semantic_relevance": 0.5,
            "information_density": 0.5,
            "coherence": 0.3,
            "redundancy": 0.1,
        },
        "production_features": {"pronunciation_deviation_events": 1.0},
        "quality_signals": {
            "audio_quality": "good",
            "background_noise": "low",
            "asr_confidence": 0.95,
            "language_match": True,
            "duration_seconds": 42.0,
            "task_complete": True,
        },
        "transcript": {
            "transcript_text": "the boy is stealing cookies",
            "segments": [
                {
                    "text": "the boy is stealing cookies",
                    "start": 0.0,
                    "end": 3.0,
                    "avg_logprob": -0.3,
                    "words": [],
                }
            ],
        },
        "raw_features": {"duration_seconds": 42.0},
        "model_version": "stub-v0",
        "needs_clinician_review": needs_review,
    }


@pytest.fixture(autouse=True)
def _stub_predict(monkeypatch):
    """Decouples these contract tests from needing a trained model artifact
    on disk for the *prediction* step -- they test the HTTP/persistence
    contract, not the ML model. (Model-explanation generation still tries
    to load models/baseline_v2 for a richer explanation and falls back
    gracefully if that artifact isn't present -- see
    backend/services/results_mapper.py::_model_explanation_for_row.)"""
    monkeypatch.setattr(assessments_module, "predict", lambda *a, **kw: _fake_predict_result())


def _create_assessment(headers, patient_id="CA-1001"):
    return client.post(
        "/assessments",
        json={"patientId": patient_id, "language": "en", "taskId": "cookie-theft"},
        headers=headers,
    )


def _upload_audio(assessment_id, headers):
    return client.post(
        f"/assessments/{assessment_id}/audio",
        files={"audio": ("recording.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
        headers=headers,
    )


def test_create_assessment_returns_id_and_pending_status(participant_headers):
    response = _create_assessment(participant_headers)

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["status"] == "pending_recording"


def test_create_assessment_requires_auth():
    response = _create_assessment(headers=None)

    assert response.status_code == 401


def test_create_assessment_403_for_a_different_patient(participant_headers):
    response = _create_assessment(participant_headers, patient_id="CA-1002")

    assert response.status_code == 403


def test_get_assessment_returns_pending_before_audio_uploaded(participant_headers):
    assessment_id = _create_assessment(participant_headers).json()["id"]

    response = client.get(f"/assessments/{assessment_id}", headers=participant_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == assessment_id
    assert body["patientId"] == "CA-1001"
    assert body["status"] == "pending_recording"
    assert body["task"] == {"id": "cookie-theft", "name": "Picture Description"}
    assert body["quality"] is None
    assert body["screening"] is None


def test_get_assessment_for_unknown_id_returns_404(participant_headers):
    response = client.get("/assessments/does-not-exist", headers=participant_headers)

    assert response.status_code == 404


def test_full_create_upload_results_flow(participant_headers, clinician_headers):
    assessment_id = _create_assessment(participant_headers).json()["id"]

    upload_response = _upload_audio(assessment_id, participant_headers)
    assert upload_response.status_code == 200
    assert upload_response.json() == {"id": assessment_id, "status": "complete"}

    # A clinician (not just the owning participant) can also read it.
    results_response = client.get(f"/assessments/{assessment_id}/results", headers=clinician_headers)
    assert results_response.status_code == 200
    body = results_response.json()

    assert body["assessment"]["id"] == assessment_id
    assert body["assessment"]["status"] == "complete"
    assert body["assessment"]["screening"]["estimate"] == pytest.approx(0.37)

    speech = body["features"]["speech"]
    assert speech["totalDurationSec"] == pytest.approx(42.0)
    assert speech["speechRateWpm"] == pytest.approx(5 / (42.0 / 60))
    assert speech["advanced"]["jitterPercent"] == pytest.approx(0.5)
    assert len(speech["advanced"]["mfccSummary"]) == 5

    linguistic = body["features"]["linguistic"]
    assert linguistic["totalWords"] == 5

    semantic = body["features"]["semantic"]
    assert semantic["conceptsIdentified"] == pytest.approx(6.0)

    assert body["transcript"]["segments"][0]["text"] == "the boy is stealing cookies"
    assert body["previousAssessment"] is None
    assert body["whatChanged"] is None
    assert body["aiSummary"] is not None
    assert body["modelExplanation"] is not None
    assert isinstance(body["modelExplanation"]["indicators"], list)


def test_results_403_for_a_different_participant(participant_headers):
    from backend.services.auth import issue_token

    assessment_id = _create_assessment(participant_headers).json()["id"]
    _upload_audio(assessment_id, participant_headers)

    other_token = issue_token("participant", "CA-1002")
    response = client.get(
        f"/assessments/{assessment_id}/results", headers={"Authorization": f"Bearer {other_token}"}
    )

    assert response.status_code == 403


def test_longitudinal_comparison_populates_previous_assessment(monkeypatch, participant_headers):
    first_id = _create_assessment(participant_headers).json()["id"]
    _upload_audio(first_id, participant_headers)

    monkeypatch.setattr(
        assessments_module,
        "predict",
        lambda *a, **kw: _fake_predict_result(risk_score=0.6, needs_review=True, word_count=20, concepts_identified=12.0),
    )
    second_id = _create_assessment(participant_headers).json()["id"]
    _upload_audio(second_id, participant_headers)

    results = client.get(f"/assessments/{second_id}/results", headers=participant_headers).json()

    assert results["previousAssessment"]["id"] == first_id
    assert results["previousFeatures"] is not None
    assert results["whatChanged"] is not None
    by_key = {c["key"]: c for c in results["whatChanged"]}
    assert by_key["conceptCoverage"]["direction"] == "increased"


def test_upload_audio_for_unknown_assessment_returns_404(participant_headers):
    response = _upload_audio("does-not-exist", participant_headers)

    assert response.status_code == 404


def test_get_results_for_unknown_assessment_returns_404(participant_headers):
    response = client.get("/assessments/does-not-exist/results", headers=participant_headers)

    assert response.status_code == 404


def test_get_results_before_audio_uploaded_returns_409(participant_headers):
    assessment_id = _create_assessment(participant_headers).json()["id"]

    response = client.get(f"/assessments/{assessment_id}/results", headers=participant_headers)

    assert response.status_code == 409


def test_upload_audio_maps_audio_processing_error_to_422(monkeypatch, participant_headers):
    from ml.features.acoustic import AudioProcessingError

    def _raise_audio_error(audio_bytes, *, task_id, language):
        raise AudioProcessingError("corrupt audio")

    monkeypatch.setattr(assessments_module, "predict", _raise_audio_error)
    assessment_id = _create_assessment(participant_headers).json()["id"]

    response = _upload_audio(assessment_id, participant_headers)

    assert response.status_code == 422


def test_list_assessments_requires_clinician(participant_headers, clinician_headers):
    participant_only = client.get("/assessments", headers=participant_headers)
    assert participant_only.status_code == 403

    as_clinician = client.get("/assessments", headers=clinician_headers)
    assert as_clinician.status_code == 200
