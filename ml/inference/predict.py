"""Inference wrapper -- the seam the backend calls into.

Loads the trained baseline pipeline once per process (module-level cache,
not once per request) and maps a raw audio upload onto the dict shape the
backend's AssessmentResult schema expects.
"""

import json
from pathlib import Path
from threading import Lock

import joblib

from ml.features.acoustic import AudioProcessingError, extract_features

__all__ = ["AudioProcessingError", "predict"]

REVIEW_THRESHOLD = 0.5  # placeholder -- no clinical basis yet, revisit once real eval exists

_cache: dict[str, tuple] = {}
_cache_lock = Lock()


def _load_model(model_dir: Path):
    key = str(model_dir)
    if key in _cache:
        return _cache[key]
    with _cache_lock:
        if key in _cache:
            return _cache[key]
        model_dir = Path(model_dir)
        metadata = json.loads((model_dir / "metadata.json").read_text())
        feature_names = json.loads((model_dir / "feature_names.json").read_text())
        pipeline = joblib.load(model_dir / f"pipeline_{metadata['selected_model']}.joblib")
        loaded = (pipeline, feature_names, metadata)
        _cache[key] = loaded
        return loaded


def predict(
    audio: bytes,
    *,
    task_id: str,
    language: str,
    model_dir: Path = Path("models/baseline_v1"),
) -> dict:
    """Runs the acoustics-only baseline on a raw audio upload.

    task_id/language are accepted for interface symmetry with the future
    ASR/NLP layer (which will branch on both) and for logging -- this
    acoustics-only baseline does not use them yet; that is intentional, not
    an oversight.

    Returns {"risk_score", "speech_features", "linguistic_features",
    "model_version", "needs_clinician_review"}. Raises AudioProcessingError
    (propagated from feature extraction) on unreadable/corrupt/too-short
    audio -- callers should map that to an HTTP 422.
    """
    pipeline, feature_names, metadata = _load_model(model_dir)

    speech_features = extract_features(audio)
    feature_vector = [[speech_features[name] for name in feature_names]]
    risk_score = float(pipeline.predict_proba(feature_vector)[0][1])

    return {
        "risk_score": risk_score,
        "speech_features": speech_features,
        "linguistic_features": {},
        "model_version": metadata["model_version"],
        "needs_clinician_review": risk_score >= REVIEW_THRESHOLD,
    }
