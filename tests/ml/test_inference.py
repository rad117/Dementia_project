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
    "model_version",
    "needs_clinician_review",
}


def _write_dummy_model(model_dir):
    model_dir.mkdir(parents=True)
    clf = DummyClassifier(strategy="constant", constant=1)
    clf.fit([[0.0], [1.0]], [0, 1])
    joblib.dump(clf, model_dir / "pipeline_dummy.joblib")
    (model_dir / "feature_names.json").write_text(json.dumps(["duration_seconds"]))
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
