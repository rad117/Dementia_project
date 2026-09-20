"""Inference wrapper -- the seam the backend calls into.

Loads the trained baseline pipeline once per process (module-level cache,
not once per request) and maps a raw audio upload onto the dict shape the
backend's AssessmentResult schema expects.

ASR (ml/asr/) and NLP (ml/nlp/) feature extraction only runs if the loaded
model's feature_names actually require columns from those layers -- an
acoustics-only model (e.g. models/baseline_v1) never triggers Whisper
transcription, so its per-request latency is unchanged. A fused model
(e.g. models/baseline_v2) does, which is meaningfully slower per request
(seconds of CPU transcription per upload) -- that tradeoff should be a
deliberate choice of which model_dir the backend points at, not implicit.
"""

import json
from pathlib import Path
from threading import Lock

import joblib

from ml.asr.transcribe import TranscriptionError, transcribe
from ml.features.acoustic import AudioProcessingError, extract_features
from ml.nlp.linguistic import LinguisticFeatureError, extract_linguistic_features

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
    """Runs the trained baseline on a raw audio upload -- acoustics-only or
    acoustic+ASR+NLP fused, depending on what model_dir's feature_names
    actually need (see module docstring).

    language is passed through to the ASR layer when triggered; task_id is
    accepted for interface symmetry/logging and not otherwise used yet.

    Returns {"risk_score", "speech_features", "linguistic_features",
    "model_version", "needs_clinician_review"}. Raises AudioProcessingError
    on unreadable/corrupt/too-short audio, or on an ASR/NLP failure when the
    model requires those features (propagated/wrapped) -- callers should
    map that to an HTTP 422.
    """
    pipeline, feature_names, metadata = _load_model(model_dir)

    speech_features = extract_features(audio)
    combined_features = dict(speech_features)
    linguistic_features: dict = {}

    if any(name not in combined_features for name in feature_names):
        try:
            asr_result = transcribe(audio, language=language)
        except TranscriptionError as exc:
            raise AudioProcessingError(f"ASR transcription failed: {exc}") from exc
        try:
            nlp_result = extract_linguistic_features(asr_result["transcript_text"])
        except LinguisticFeatureError as exc:
            raise AudioProcessingError(f"Linguistic feature extraction failed: {exc}") from exc

        linguistic_features = {**asr_result, **nlp_result}
        combined_features.update(
            {
                "asr_word_count": asr_result["word_count"],
                "avg_logprob": asr_result["avg_logprob"],
                "no_speech_prob": asr_result["no_speech_prob"],
                **nlp_result,
            }
        )

    feature_vector = [[combined_features[name] for name in feature_names]]
    risk_score = float(pipeline.predict_proba(feature_vector)[0][1])

    return {
        "risk_score": risk_score,
        "speech_features": speech_features,
        "linguistic_features": linguistic_features,
        "model_version": metadata["model_version"],
        "needs_clinician_review": risk_score >= REVIEW_THRESHOLD,
    }
