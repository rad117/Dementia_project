import io
import json

import joblib
import numpy as np
import pytest
import soundfile as sf
from sklearn.dummy import DummyClassifier

from ml.features.acoustic import AudioProcessingError
from ml.inference import predict as predict_module
from ml.inference.predict import predict

_EXPECTED_KEYS = {
    "risk_score",
    "speech_features",
    "linguistic_features",
    "semantic_features",
    "production_features",
    "quality_signals",
    "transcript",
    "raw_features",
    "model_version",
    "needs_clinician_review",
}


def _write_dummy_model(model_dir, feature_names=("duration_seconds",)):
    model_dir.mkdir(parents=True)
    clf = DummyClassifier(strategy="constant", constant=1)
    clf.fit([[0.0] * len(feature_names), [1.0] * len(feature_names)], [0, 1])
    joblib.dump(clf, model_dir / "pipeline_dummy.joblib")
    (model_dir / "feature_names.json").write_text(json.dumps(list(feature_names)))
    (model_dir / "metadata.json").write_text(
        json.dumps({"selected_model": "dummy", "model_version": "test-dummy-v0"})
    )


def _sine_wave_bytes(seconds=1.0, sr=16000, freq=220.0):
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    samples = (0.5 * np.sin(2 * np.pi * freq * t)).astype("float32")
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _clear_model_cache():
    predict_module._cache.clear()
    yield
    predict_module._cache.clear()


def test_predict_returns_expected_contract(tmp_path):
    model_dir = tmp_path / "dummy_model"
    _write_dummy_model(model_dir)

    result = predict(_sine_wave_bytes(), task_id="cookie-theft", language="en", model_dir=model_dir)

    assert set(result.keys()) == _EXPECTED_KEYS
    assert isinstance(result["risk_score"], float)
    assert 0.0 <= result["risk_score"] <= 1.0
    assert isinstance(result["speech_features"], dict)
    assert "duration_seconds" in result["speech_features"]
    assert result["linguistic_features"] == {}
    assert result["semantic_features"] == {}
    assert result["production_features"] == {}
    assert result["quality_signals"] == {}
    assert result["transcript"] is None
    assert result["model_version"] == "test-dummy-v0"
    assert isinstance(result["needs_clinician_review"], bool)


def test_predict_needs_clinician_review_follows_threshold(tmp_path):
    model_dir = tmp_path / "dummy_model"
    _write_dummy_model(model_dir)

    result = predict(_sine_wave_bytes(), task_id="cookie-theft", language="en", model_dir=model_dir)

    # DummyClassifier(strategy="constant", constant=1) always predicts class 1
    # with probability 1.0, which must clear the review threshold.
    assert result["risk_score"] == pytest.approx(1.0)
    assert result["needs_clinician_review"] is True


def test_predict_propagates_audio_processing_error(tmp_path):
    model_dir = tmp_path / "dummy_model"
    _write_dummy_model(model_dir)

    with pytest.raises(AudioProcessingError):
        predict(b"not audio", task_id="cookie-theft", language="en", model_dir=model_dir)


def test_predict_acoustic_only_model_never_calls_asr(tmp_path, monkeypatch):
    """An acoustics-only model's feature_names never need ASR/NLP columns,
    so predict() must not call transcribe() at all -- this is what keeps
    models/baseline_v1's per-request latency unchanged."""

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("transcribe() should not be called for an acoustics-only model")

    monkeypatch.setattr("ml.inference.predict.transcribe", _fail_if_called)

    model_dir = tmp_path / "dummy_model"
    _write_dummy_model(model_dir)

    result = predict(_sine_wave_bytes(), task_id="cookie-theft", language="en", model_dir=model_dir)

    assert result["linguistic_features"] == {}


def test_predict_fused_model_calls_asr_and_nlp(tmp_path, monkeypatch):
    fused_feature_names = ["duration_seconds", "asr_word_count", "type_token_ratio"]

    def _fake_transcribe(audio, *, language):
        return {
            "transcript_text": "the boy is stealing cookies",
            "word_count": 5,
            "avg_logprob": -0.3,
            "no_speech_prob": 0.1,
            "duration_seconds": 1.0,
        }

    def _fake_extract_linguistic_features(transcript_text):
        return {"type_token_ratio": 1.0, "word_count": 5}

    monkeypatch.setattr("ml.inference.predict.transcribe", _fake_transcribe)
    monkeypatch.setattr(
        "ml.inference.predict.extract_linguistic_features", _fake_extract_linguistic_features
    )

    model_dir = tmp_path / "fused_model"
    _write_dummy_model(model_dir, feature_names=fused_feature_names)

    result = predict(_sine_wave_bytes(), task_id="cookie-theft", language="en", model_dir=model_dir)

    assert result["linguistic_features"]["transcript_text"] == "the boy is stealing cookies"
    assert result["linguistic_features"]["type_token_ratio"] == 1.0
    assert isinstance(result["risk_score"], float)


def test_predict_fused_model_wraps_transcription_error(tmp_path, monkeypatch):
    from ml.asr.transcribe import TranscriptionError

    def _fake_transcribe(audio, *, language):
        raise TranscriptionError("decode failed")

    monkeypatch.setattr("ml.inference.predict.transcribe", _fake_transcribe)

    model_dir = tmp_path / "fused_model"
    _write_dummy_model(model_dir, feature_names=["duration_seconds", "asr_word_count"])

    with pytest.raises(AudioProcessingError):
        predict(_sine_wave_bytes(), task_id="cookie-theft", language="en", model_dir=model_dir)
