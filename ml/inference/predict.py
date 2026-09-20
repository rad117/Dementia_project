"""Inference wrapper -- the seam the backend calls into.

Loads the trained baseline pipeline once per process (module-level cache,
not once per request) and maps a raw audio upload onto the dict shape the
backend's AssessmentResult schema expects.

ASR (ml/asr/) and NLP (ml/nlp/) feature extraction only runs if the loaded
model's feature_names actually require columns from those layers -- an
acoustics-only model (e.g. models/baseline_v1) never triggers Whisper
transcription, so its per-request latency is unchanged. A fused model
(e.g. models/baseline_v2) does, which is meaningfully slower per request
(seconds of CPU transcription per upload).

Decision made (2026-09-20): models/baseline_v2 (fused) is the default
model_dir below and therefore what the backend serves by default, trading
that per-request ASR latency for a substantial cross-validated ROC-AUC
gain over baseline_v1. models/baseline_v1 remains available as a fast
acoustics-only fallback by passing model_dir explicitly.
"""

import json
from pathlib import Path
from threading import Lock

import joblib

from ml.asr.transcribe import TranscriptionError, transcribe
from ml.features.acoustic import AudioProcessingError, extract_features
from ml.nlp.disfluency import extract_disfluency_features
from ml.nlp.linguistic import LinguisticFeatureError, extract_linguistic_features
from ml.nlp.semantic import extract_semantic_features

__all__ = ["AudioProcessingError", "predict"]

DEFAULT_REVIEW_THRESHOLD = 0.5  # fallback only -- real models carry their own
# review_threshold in metadata.json (Youden's index on the held-out test split,
# see ml/training/train_baseline.py) -- a statistically principled cutoff, not
# a clinically validated one. This constant only covers models trained before
# that field existed.

# Below this ASR word confidence, a word is treated as a possible
# pronunciation/articulation deviation -- an ASR-confidence proxy, not a
# validated clinical measure (accent, dialect, recording quality, and ASR
# model limitations all lower word confidence too). True phoneme-level
# deviation detection is out of scope (see docs/plan: no reference
# transcript exists for free-description speech to align against, and
# a real phone recognizer would require a torch dependency this project
# has deliberately avoided elsewhere).
_PRONUNCIATION_CONFIDENCE_THRESHOLD = 0.6
_GOOD_ASR_CONFIDENCE = 0.9
_MIN_TASK_DURATION_SECONDS = 10.0

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


def _quality_signals(asr_result: dict, speech_features: dict, requested_language: str) -> dict:
    asr_confidence = 1.0 - asr_result["no_speech_prob"]
    good = asr_confidence > _GOOD_ASR_CONFIDENCE
    detected_language = asr_result.get("detected_language", requested_language)
    duration_seconds = speech_features["duration_seconds"]
    return {
        "audio_quality": "good" if good else "fair",
        "background_noise": "low" if good else "moderate",
        "asr_confidence": asr_confidence,
        "language_match": detected_language == requested_language,
        "duration_seconds": duration_seconds,
        "task_complete": duration_seconds >= _MIN_TASK_DURATION_SECONDS and asr_result["word_count"] > 0,
    }


def _pronunciation_deviation_events(asr_result: dict) -> float:
    flat_words = [w for segment in asr_result.get("segments", []) for w in segment.get("words", [])]
    return float(sum(1 for w in flat_words if w["probability"] < _PRONUNCIATION_CONFIDENCE_THRESHOLD))


def predict(
    audio: bytes,
    *,
    task_id: str,
    language: str,
    model_dir: Path = Path("models/baseline_v2"),
) -> dict:
    """Runs the trained baseline on a raw audio upload -- acoustics-only or
    acoustic+ASR+NLP fused, depending on what model_dir's feature_names
    actually need (see module docstring).

    language is passed through to the ASR layer when triggered; task_id is
    accepted for interface symmetry/logging and not otherwise used yet.

    Returns {"risk_score", "speech_features", "linguistic_features",
    "semantic_features", "production_features", "quality_signals",
    "transcript", "raw_features", "model_version",
    "needs_clinician_review"}. raw_features is the flat dict the model's
    feature vector was actually built from (speech_features plus ASR/NLP
    passthrough) -- persisted so a later model-explanation call can
    reconstruct the same input without re-running inference. The
    ASR-dependent fields are empty dicts / None on an acoustics-only model
    (see module docstring for why ASR/NLP is conditionally skipped).
    Raises AudioProcessingError on unreadable/corrupt/too-short audio, or
    on an ASR/NLP failure when the model requires those features
    (propagated/wrapped) -- callers should map that to an HTTP 422.
    """
    pipeline, feature_names, metadata = _load_model(model_dir)

    speech_features = extract_features(audio)
    combined_features = dict(speech_features)
    linguistic_features: dict = {}
    semantic_features: dict = {}
    production_features: dict = {}
    quality_signals: dict = {}
    transcript: dict | None = None

    if any(name not in combined_features for name in feature_names):
        try:
            asr_result = transcribe(audio, language=language)
        except TranscriptionError as exc:
            raise AudioProcessingError(f"ASR transcription failed: {exc}") from exc
        try:
            nlp_result = extract_linguistic_features(asr_result["transcript_text"])
            semantic_result = extract_semantic_features(asr_result["transcript_text"])
            disfluency_result = extract_disfluency_features(
                asr_result["transcript_text"], segments=asr_result.get("segments")
            )
        except LinguisticFeatureError as exc:
            raise AudioProcessingError(f"Linguistic feature extraction failed: {exc}") from exc

        linguistic_features = {**asr_result, **nlp_result, **disfluency_result}
        linguistic_features.pop("segments", None)  # exposed separately as `transcript`
        semantic_features = semantic_result
        production_features = {
            "pronunciation_deviation_events": _pronunciation_deviation_events(asr_result)
        }
        quality_signals = _quality_signals(asr_result, speech_features, language)
        transcript = {
            "transcript_text": asr_result["transcript_text"],
            "segments": asr_result.get("segments", []),
        }
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
        "semantic_features": semantic_features,
        "production_features": production_features,
        "quality_signals": quality_signals,
        "transcript": transcript,
        "raw_features": combined_features,
        "model_version": metadata["model_version"],
        "needs_clinician_review": risk_score >= metadata.get("review_threshold", DEFAULT_REVIEW_THRESHOLD),
    }
