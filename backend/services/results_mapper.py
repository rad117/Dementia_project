"""Adapter layer: turns a raw assessments DB row (+ optional previous row
for longitudinal comparison) into the nested dict shape
backend/schemas/results.py's models validate -- all frontend-shape
knowledge (field renames, unit conversions, grouping) lives here, so
backend/db.py stays a dumb generic JSON-blob store and ml/ stays
ML-native (flat, snake_case, unconverted units).

Every function here returns plain dicts with snake_case keys matching
the Pydantic models' field names (not yet camelCase-aliased) --
backend/routes/assessments.py passes these straight into
AssessmentInfo(**dict)/AssessmentResultsV2(**dict), relying on
populate_by_name=True.
"""

import json
from pathlib import Path

from backend import db
from backend.services import narratives
from backend.services.tasks import get_task
from ml.inference.predict import _load_model
from ml.nlp.annotate import annotate_transcript_segments

_MODELS_ROOT = Path("models")
_DEFAULT_MODEL_DIR = Path("models/baseline_v2")


def _resolve_model_dir(model_version: str | None) -> Path:
    """Finds the model_dir whose metadata.json's model_version matches the
    version stamped on this assessment's row -- so an old assessment
    scored by a since-superseded model still gets explained by the model
    that actually produced its score, not whatever is live now. Falls
    back to the current default if no match is found (e.g. legacy rows
    from before model_version was recorded)."""
    if model_version and _MODELS_ROOT.exists():
        for candidate in _MODELS_ROOT.iterdir():
            metadata_path = candidate / "metadata.json"
            if not metadata_path.exists():
                continue
            try:
                metadata = json.loads(metadata_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if metadata.get("model_version") == model_version:
                return candidate
    return _DEFAULT_MODEL_DIR


def _load_json(row: dict, column: str) -> dict:
    raw = row.get(column)
    return json.loads(raw) if raw else {}


def build_assessment_info(row: dict) -> dict:
    task = get_task(row["task_id"])
    is_complete = row["status"] == "complete"

    quality = None
    screening = None
    if is_complete:
        quality_raw = _load_json(row, "quality_signals")
        speech_raw = _load_json(row, "speech_features")
        quality = {
            "audio_quality": quality_raw.get("audio_quality", "unknown"),
            "background_noise": quality_raw.get("background_noise", "unknown"),
            "asr_confidence": quality_raw.get("asr_confidence", 0.0),
            "language_match": quality_raw.get("language_match", True),
            "duration_seconds": quality_raw.get("duration_seconds", speech_raw.get("duration_seconds", 0.0)),
            "task_complete": quality_raw.get("task_complete", True),
        }
        screening = {
            "estimate": row["risk_score"],
            "needs_clinician_review": bool(row["needs_clinician_review"]),
            "model_version": row["model_version"],
        }

    return {
        "id": row["id"],
        "patient_id": row["patient_id"],
        "date": row["created_at"][:10],
        "language": row["language"],
        "task": {"id": row["task_id"], "name": task["name"]},
        "quality": quality,
        "screening": screening,
        "status": row["status"],
    }


def build_feature_set(row: dict) -> dict | None:
    if row["status"] != "complete":
        return None

    speech_raw = _load_json(row, "speech_features")
    linguistic_raw = _load_json(row, "linguistic_features")
    semantic_raw = _load_json(row, "semantic_features")
    production_raw = _load_json(row, "production_features")
    quality_raw = _load_json(row, "quality_signals")

    duration = speech_raw.get("duration_seconds", 0.0)
    total_pause = speech_raw.get("total_pause_duration_seconds", 0.0)
    pause_count = speech_raw.get("pause_count", 0.0)
    pitch_mean = speech_raw.get("pitch_mean_hz", 0.0)
    word_count = linguistic_raw.get("word_count", 0)
    speech_duration = max(duration - total_pause, 0.0)

    speech = {
        "total_duration_sec": duration,
        "speech_duration_sec": speech_duration,
        "speech_silence_ratio": 1.0 - speech_raw.get("pause_ratio", 0.0),
        "pause_ratio_percent": speech_raw.get("pause_ratio", 0.0) * 100,
        "speech_rate_wpm": (word_count / (duration / 60)) if duration > 0 else 0.0,
        "articulation_rate_wpm": (word_count / (speech_duration / 60)) if speech_duration > 0 else 0.0,
        "pause_count": pause_count,
        "pause_frequency_per_min": (pause_count / (duration / 60)) if duration > 0 else 0.0,
        "mean_pause_sec": (total_pause / pause_count) if pause_count > 0 else 0.0,
        "longest_pause_sec": speech_raw.get("longest_pause_seconds", 0.0),
        "response_latency_sec": speech_raw.get("first_speech_onset_seconds", 0.0),
        "voice_breaks": speech_raw.get("voice_breaks_count", 0.0),
        "mean_f0": pitch_mean,
        "f0_variability": (speech_raw.get("pitch_std_hz", 0.0) / pitch_mean) if pitch_mean > 0 else 0.0,
        "energy_rms": speech_raw.get("energy_rms_mean", 0.0),
        "advanced": {
            "jitter_percent": speech_raw.get("jitter_percent", 0.0),
            "shimmer_percent": speech_raw.get("shimmer_percent", 0.0),
            "hnr_db": speech_raw.get("hnr_db", 0.0),
            "spectral_centroid_hz": speech_raw.get("spectral_centroid_hz_mean", 0.0),
            "mfcc_summary": [speech_raw.get(f"mfcc_{i}_mean", 0.0) for i in range(1, 6)],
        },
    }

    linguistic = {
        "total_words": word_count,
        "unique_words": linguistic_raw.get("unique_word_count", 0),
        "vocabulary_diversity": linguistic_raw.get("type_token_ratio", 0.0),
        "repetitions": linguistic_raw.get("repeated_word_count", 0.0),
        "revisions": linguistic_raw.get("revision_marker_count", 0.0),
        "generic_substitutions": linguistic_raw.get("generic_substitution_count", 0.0),
        "fillers": linguistic_raw.get("filler_word_count", 0.0),
        "retrieval_events": linguistic_raw.get("retrieval_event_count", 0.0),
        "avg_sentence_length": linguistic_raw.get("words_per_sentence", 0.0),
        "incomplete_utterances": linguistic_raw.get("incomplete_utterance_count", 0.0),
        "syntactic_complexity": linguistic_raw.get("syntactic_complexity_score", 0.0),
    }

    semantic = {
        "concept_coverage": semantic_raw.get("concept_coverage", 0.0),
        "concepts_identified": semantic_raw.get("concepts_identified", 0.0),
        "concepts_expected": semantic_raw.get("concepts_expected", 0.0),
        "semantic_relevance": semantic_raw.get("semantic_relevance", 0.0),
        "information_density": semantic_raw.get("information_density", 0.0),
        "coherence": semantic_raw.get("coherence", 0.0),
        "redundancy": semantic_raw.get("redundancy", 0.0),
    }

    production = {
        "pronunciation_deviation_events": production_raw.get("pronunciation_deviation_events"),
        "phoneme_deviation_events": None,  # out of scope -- see ml/inference/predict.py
    }

    quality = {
        "audio_quality": quality_raw.get("audio_quality", "unknown"),
        "background_noise": quality_raw.get("background_noise", "unknown"),
        "asr_confidence": quality_raw.get("asr_confidence", 0.0),
        "language_match": quality_raw.get("language_match", True),
        "duration_seconds": quality_raw.get("duration_seconds", duration),
        "task_complete": quality_raw.get("task_complete", True),
    }

    return {
        "speech": speech,
        "linguistic": linguistic,
        "semantic": semantic,
        "production": production,
        "quality": quality,
    }


def build_transcript(row: dict) -> dict | None:
    transcript_raw = row.get("transcript")
    if not transcript_raw:
        return None
    parsed = json.loads(transcript_raw)
    segments = annotate_transcript_segments(parsed.get("segments", []))
    for segment in segments:
        segment["id"] = f"{row['id']}-{segment['id']}"

    note = (
        "Transcript generated by automatic speech recognition (Whisper); segment "
        "classification (filler/repetition/revision/concept) is a rule-based heuristic "
        "and may not be fully accurate."
    )
    return {
        "assessment_id": row["id"],
        "language": row["language"],
        "generated_note": note,
        "segments": segments,
    }


def find_previous_assessment_row(patient_id: str, current_id: str) -> dict | None:
    history = db.list_assessments_by_patient(patient_id)
    idx = next((i for i, r in enumerate(history) if r["id"] == current_id), None)
    if idx is None or idx + 1 >= len(history):
        return None
    return history[idx + 1]


def _model_explanation_for_row(row: dict, feature_set: dict) -> dict:
    model_dir = _resolve_model_dir(row.get("model_version"))
    raw_features = _load_json(row, "raw_features")
    try:
        _, feature_names, metadata = _load_model(model_dir)
    except Exception:
        return {
            "indicators": ["Model explanation is not available for this assessment."],
            "model_version": row.get("model_version", "unknown"),
            "is_demo_explanation": True,
        }
    return narratives.generate_model_explanation(
        raw_features=raw_features, feature_names=feature_names, metadata=metadata, model_dir=model_dir
    )


def build_results(row: dict, previous_row: dict | None = None) -> dict:
    assessment = build_assessment_info(row)
    features = build_feature_set(row)

    if features is None:
        return {
            "assessment": assessment,
            "features": None,
            "transcript": None,
            "previous_assessment": None,
            "previous_features": None,
            "what_changed": None,
            "ai_summary": None,
            "model_explanation": None,
        }

    previous_assessment = build_assessment_info(previous_row) if previous_row else None
    previous_features = build_feature_set(previous_row) if previous_row else None
    what_changed = narratives.compute_what_changed(features, previous_features)
    ai_summary = narratives.generate_ai_summary(
        assessment=assessment,
        features=features,
        previous_features=previous_features,
        what_changed=what_changed,
        quality=features["quality"],
    )
    model_explanation = _model_explanation_for_row(row, features)

    return {
        "assessment": assessment,
        "features": features,
        "transcript": build_transcript(row),
        "previous_assessment": previous_assessment,
        "previous_features": previous_features,
        "what_changed": what_changed,
        "ai_summary": ai_summary,
        "model_explanation": model_explanation,
    }
