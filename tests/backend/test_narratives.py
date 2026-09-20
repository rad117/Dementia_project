import json
from pathlib import Path

import pytest

from backend.services.narratives import (
    compute_what_changed,
    generate_ai_summary,
    generate_model_explanation,
)


def _features(speech_rate=100.0, pause_freq=12.0, latency=2.0, concept_coverage=0.6, vocab_diversity=0.6):
    return {
        "speech": {
            "speech_rate_wpm": speech_rate,
            "pause_frequency_per_min": pause_freq,
            "response_latency_sec": latency,
            "pause_ratio_percent": 20.0,
            "mean_pause_sec": 0.9,
            "longest_pause_sec": 2.0,
        },
        "linguistic": {
            "vocabulary_diversity": vocab_diversity,
            "total_words": 80.0,
            "unique_words": 48.0,
            "fillers": 3.0,
            "repetitions": 1.0,
        },
        "semantic": {
            "concept_coverage": concept_coverage,
            "concepts_identified": 9.0,
            "concepts_expected": 15.0,
        },
    }


def _quality(asr_confidence=0.9, audio_quality="good", background_noise="low", duration=60.0):
    return {
        "asr_confidence": asr_confidence,
        "audio_quality": audio_quality,
        "background_noise": background_noise,
        "duration_seconds": duration,
    }


def _assessment(needs_review=False):
    return {
        "id": "A-1",
        "language": "en",
        "task": {"name": "Picture Description"},
        "screening": {"estimate": 0.4, "needs_clinician_review": needs_review, "model_version": "v1"},
    }


def test_compute_what_changed_returns_none_without_previous():
    assert compute_what_changed(_features(), None) is None


def test_compute_what_changed_flags_increase_and_decrease():
    current = _features(speech_rate=80.0, concept_coverage=0.5)
    previous = _features(speech_rate=100.0, concept_coverage=0.6)

    items = compute_what_changed(current, previous)
    by_key = {i["key"]: i for i in items}

    assert by_key["speechRateWpm"]["direction"] == "decreased"
    assert by_key["conceptCoverage"]["direction"] == "decreased"


def test_compute_what_changed_steady_within_noise_floor():
    current = _features(speech_rate=100.0)
    previous = _features(speech_rate=100.5)  # well under 3% noise floor

    items = compute_what_changed(current, previous)
    by_key = {i["key"]: i for i in items}

    assert by_key["speechRateWpm"]["direction"] == "steady"


def test_generate_ai_summary_returns_expected_sections():
    features = _features()
    summary = generate_ai_summary(
        assessment=_assessment(),
        features=features,
        previous_features=None,
        what_changed=None,
        quality=_quality(),
    )

    assert "overview" in summary
    assert summary["observed_changes"] == ["No previous assessment is available for comparison."]
    assert len(summary["speech_patterns"]) == 3
    assert len(summary["language_patterns"]) == 3
    assert "disclaimer" in summary


def test_generate_ai_summary_flags_review_when_needed():
    summary = generate_ai_summary(
        assessment=_assessment(needs_review=True),
        features=_features(),
        previous_features=None,
        what_changed=None,
        quality=_quality(),
    )

    assert any("recommend clinician review" in p for p in summary["review_points"])


def test_generate_ai_summary_flags_low_asr_confidence():
    summary = generate_ai_summary(
        assessment=_assessment(),
        features=_features(),
        previous_features=None,
        what_changed=None,
        quality=_quality(asr_confidence=0.5),
    )

    assert any("Lower ASR confidence" in p for p in summary["review_points"])


_BASELINE_V2 = Path("models/baseline_v2")


@pytest.mark.skipif(not _BASELINE_V2.exists(), reason="trained baseline_v2 model artifact not present locally")
def test_generate_model_explanation_uses_real_shap_for_rf_model():
    feature_names = json.loads((_BASELINE_V2 / "feature_names.json").read_text())
    metadata = json.loads((_BASELINE_V2 / "metadata.json").read_text())
    raw_features = {name: 0.5 for name in feature_names}

    explanation = generate_model_explanation(
        raw_features=raw_features, feature_names=feature_names, metadata=metadata, model_dir=_BASELINE_V2
    )

    assert explanation["is_demo_explanation"] is False
    assert explanation["model_version"] == metadata["model_version"]
    assert 1 <= len(explanation["indicators"]) <= 5
    assert all(isinstance(i, str) for i in explanation["indicators"])


def test_generate_model_explanation_falls_back_gracefully_on_missing_model():
    explanation = generate_model_explanation(
        raw_features={"duration_seconds": 1.0},
        feature_names=["duration_seconds"],
        metadata={"model_version": "missing-v0", "selected_model": "rf"},
        model_dir=Path("models/does-not-exist"),
    )

    assert explanation["is_demo_explanation"] is True
    assert explanation["model_version"] == "missing-v0"
