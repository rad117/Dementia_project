"""Clinician-facing narrative generation: longitudinal change summary, a
deterministic template-based AI summary, and a real per-instance model
explanation.

compute_what_changed / generate_ai_summary are direct ports of
frontend/src/utils/clinicalNarratives.js's computeWhatChanged /
generateAiSummary (same tracked metrics, same 3% noise floor, same
section structure) -- kept in lockstep with that file so clinician-facing
wording stays consistent between the demo and the real backend. Operates
on the same nested feature dict shape backend/services/results_mapper.py
builds (snake_case keys matching backend/schemas/results.py's field
names, not yet camelCase-aliased).

generate_model_explanation is NOT a mock port -- it computes real
per-instance feature contributions via SHAP for the live default model
(a Random Forest, where feature_importances_ alone is only a global
ranking and can't explain a single prediction) or a coefficient-based
explanation for a LogisticRegression pipeline. Falls back to a plain
"not available" message rather than raising, since model explanation is
supplementary -- a results page should still render on trained-model
version mismatches, missing model artifacts, etc.
"""

from pathlib import Path

import numpy as np

from ml.inference.predict import _load_model

_NOISE_FLOOR_PERCENT = 3

_CHANGE_METRICS = [
    {
        "key": "speechRateWpm",
        "label": "Speech rate",
        "unit": "WPM",
        "higher_is_better": True,
        "get": lambda f: f["speech"]["speech_rate_wpm"],
    },
    {
        "key": "pauseFrequencyPerMin",
        "label": "Pause frequency",
        "unit": "per min",
        "higher_is_better": False,
        "get": lambda f: f["speech"]["pause_frequency_per_min"],
    },
    {
        "key": "responseLatencySec",
        "label": "Response latency",
        "unit": "sec",
        "higher_is_better": False,
        "get": lambda f: f["speech"]["response_latency_sec"],
    },
    {
        "key": "conceptCoverage",
        "label": "Concept coverage",
        "unit": "",
        "higher_is_better": True,
        "get": lambda f: f["semantic"]["concept_coverage"],
    },
    {
        "key": "vocabularyDiversity",
        "label": "Vocabulary diversity",
        "unit": "",
        "higher_is_better": True,
        "get": lambda f: f["linguistic"]["vocabulary_diversity"],
    },
]


def compute_what_changed(current_features: dict, previous_features: dict | None) -> list[dict] | None:
    if not previous_features:
        return None

    items = []
    for metric in _CHANGE_METRICS:
        current_value = metric["get"](current_features)
        previous_value = metric["get"](previous_features)
        delta = current_value - previous_value
        percent = 0.0 if previous_value == 0 else (delta / abs(previous_value)) * 100
        direction = "steady"
        if abs(percent) >= _NOISE_FLOOR_PERCENT:
            direction = "increased" if delta > 0 else "decreased"
        items.append(
            {
                "key": metric["key"],
                "label": metric["label"],
                "unit": metric["unit"],
                "higher_is_better": metric["higher_is_better"],
                "current_value": current_value,
                "previous_value": previous_value,
                "percent": round(abs(percent)),
                "direction": direction,
            }
        )
    return items


def generate_ai_summary(
    *,
    assessment: dict,
    features: dict,
    previous_features: dict | None,
    what_changed: list[dict] | None,
    quality: dict,
) -> dict:
    screening = assessment["screening"]
    task_name = assessment["task"]["name"].lower()
    overview = (
        f"Assessment {assessment['id']} recorded a {task_name} task in {assessment['language']}, "
        f"lasting {quality['duration_seconds']:.0f} seconds. "
        f"Screening estimate: {screening['estimate'] * 100:.0f}/100 (illustrative)."
    )

    non_steady = [c for c in (what_changed or []) if c["direction"] != "steady"]
    if what_changed and non_steady:
        observed_changes = [
            f"{c['label']} {c['direction']} by {c['percent']:.0f}% versus the previous assessment."
            for c in non_steady
        ]
    elif previous_features:
        observed_changes = [
            "No measured indicator changed by more than the noise threshold versus the previous assessment."
        ]
    else:
        observed_changes = ["No previous assessment is available for comparison."]

    speech = features["speech"]
    speech_patterns = [
        f"Speech rate measured at {speech['speech_rate_wpm']:g} WPM with a pause ratio of "
        f"{speech['pause_ratio_percent']:g}%.",
        f"Mean pause duration {speech['mean_pause_sec']:g}s; longest pause {speech['longest_pause_sec']:g}s.",
        f"Response latency measured at {speech['response_latency_sec']:g}s.",
    ]

    linguistic = features["linguistic"]
    semantic = features["semantic"]
    language_patterns = [
        f"Vocabulary diversity {linguistic['vocabulary_diversity']:g} across "
        f"{linguistic['total_words']:g} total words ({linguistic['unique_words']:g} unique).",
        f"{linguistic['fillers']:g} filler instances and {linguistic['repetitions']:g} repetitions observed.",
        f"Concept coverage: {semantic['concepts_identified']:g} of "
        f"{semantic['concepts_expected']:g} expected task concepts identified.",
    ]

    assessment_quality = [
        f"Audio quality: {quality['audio_quality']}. Background noise: {quality['background_noise']}.",
        f"ASR confidence: {quality['asr_confidence'] * 100:.0f}%.",
        (
            "Recording quality may limit the reliability of derived indicators."
            if quality["audio_quality"] == "poor" or quality["asr_confidence"] < 0.75
            else "Recording quality was sufficient for the derived indicators."
        ),
    ]

    review_points = []
    if screening["needs_clinician_review"]:
        review_points.append(
            "Composite screening estimate is elevated relative to this patient's baseline — "
            "recommend clinician review."
        )
    if what_changed and any(c["key"] == "conceptCoverage" and c["direction"] == "decreased" for c in what_changed):
        review_points.append("Concept coverage decreased versus the previous assessment.")
    if what_changed and any(
        c["key"] == "responseLatencySec" and c["direction"] == "increased" for c in what_changed
    ):
        review_points.append("Response latency increased versus the previous assessment.")
    if quality["asr_confidence"] < 0.75:
        review_points.append(
            "Lower ASR confidence — consider requesting a repeat recording in quieter conditions."
        )
    if not review_points:
        review_points.append("No indicator-based review flags were raised for this assessment.")

    return {
        "overview": overview,
        "observed_changes": observed_changes,
        "speech_patterns": speech_patterns,
        "language_patterns": language_patterns,
        "assessment_quality": assessment_quality,
        "review_points": review_points,
        "disclaimer": (
            "This is a deterministic, structured-data summary generated for clinical review. "
            "It is not a diagnosis and does not represent patient-reported history."
        ),
    }


# Friendly clinician-facing labels for the ~51 raw ml/ feature_names.json
# columns. Falls back to a title-cased raw name for anything not listed
# here (e.g. a future retrain adds a column) rather than erroring.
FEATURE_LABELS = {
    "duration_seconds": "Recording duration",
    "pause_count": "Pause count",
    "total_pause_duration_seconds": "Total pause duration",
    "pause_ratio": "Pause ratio",
    "voiced_rate_per_min": "Voiced segments per minute",
    "longest_pause_seconds": "Longest pause",
    "first_speech_onset_seconds": "Response latency",
    "pitch_mean_hz": "Mean pitch (F0)",
    "pitch_std_hz": "Pitch variability",
    "voice_breaks_count": "Voice breaks",
    "energy_rms_mean": "Mean energy (intensity)",
    "energy_rms_std": "Energy variability",
    "jitter_percent": "Jitter",
    "shimmer_percent": "Shimmer",
    "hnr_db": "Harmonics-to-noise ratio",
    "spectral_centroid_hz_mean": "Spectral centroid",
    "asr_word_count": "Word count (ASR)",
    "avg_logprob": "ASR confidence (log-probability)",
    "no_speech_prob": "Probability of no speech",
    "word_count": "Word count",
    "unique_word_count": "Unique word count",
    "type_token_ratio": "Vocabulary diversity",
    "mean_word_length": "Mean word length",
    "sentence_count": "Sentence count",
    "words_per_sentence": "Words per sentence",
    "pronoun_ratio": "Pronoun usage",
    "filler_word_count": "Filler word count",
    "filler_word_ratio": "Filler word ratio",
    "repeated_bigram_ratio": "Repetition ratio",
    "cookie_theft_concept_count": "Concepts identified",
    "cookie_theft_concept_ratio": "Concept coverage",
    "mean_adjacent_sentence_similarity": "Sentence coherence",
    **{f"mfcc_{i}_mean": f"MFCC {i} (mean)" for i in range(1, 14)},
    **{f"mfcc_{i}_std": f"MFCC {i} (variability)" for i in range(1, 14)},
}

_TOP_N_INDICATORS = 5


def _label(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " ").capitalize())


def _shap_contributions(pipeline, feature_names: list[str], vector) -> dict[str, float]:
    import shap

    explainer = shap.TreeExplainer(pipeline)
    shap_values = explainer.shap_values(vector)
    # TreeExplainer's output shape varies by shap version: (1, n_features,
    # n_classes) on recent versions, or a list of per-class arrays on
    # older ones. Either way we want the positive ("needs review") class.
    if hasattr(shap_values, "ndim") and shap_values.ndim == 3:
        values = shap_values[0, :, 1]
    elif isinstance(shap_values, list):
        values = shap_values[1][0]
    else:
        values = shap_values[0]
    return dict(zip(feature_names, values))


def _coefficient_contributions(pipeline, feature_names: list[str], vector) -> dict[str, float]:
    scaler = pipeline.named_steps["scaler"]
    clf = pipeline.named_steps["clf"]
    standardized = scaler.transform(vector)[0]
    contributions = standardized * clf.coef_[0]
    return dict(zip(feature_names, contributions))


def generate_model_explanation(
    *, raw_features: dict, feature_names: list[str], metadata: dict, model_dir: Path
) -> dict:
    """Real per-instance model explanation for the model that actually
    produced this assessment's risk_score -- not the mock's fixed
    threshold-based demo logic. Falls back to a plain unavailable message
    (isDemoExplanation stays True) rather than raising, since a missing
    explanation shouldn't block rendering the rest of the results page."""
    model_version = metadata.get("model_version", "unknown")
    try:
        pipeline, _, _ = _load_model(model_dir)
        vector = np.array([[raw_features[name] for name in feature_names]])
        selected = metadata.get("selected_model")
        if selected == "rf":
            contributions = _shap_contributions(pipeline, feature_names, vector)
        elif selected == "logreg":
            contributions = _coefficient_contributions(pipeline, feature_names, vector)
        else:
            raise ValueError(f"No explanation strategy for model type: {selected!r}")
    except Exception:
        return {
            "indicators": ["Model explanation is not available for this assessment."],
            "model_version": model_version,
            "is_demo_explanation": True,
        }

    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:_TOP_N_INDICATORS]
    indicators = [
        f"{'Higher' if value > 0 else 'Lower'} {_label(name).lower()}"
        for name, value in ranked
        if abs(value) > 1e-9
    ]
    if not indicators:
        indicators = ["No indicator contributed meaningfully to this assessment's score."]

    return {"indicators": indicators, "model_version": model_version, "is_demo_explanation": False}
