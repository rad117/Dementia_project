import pytest

from ml.nlp.disfluency import extract_disfluency_features

_EXPECTED_KEYS = {
    "repeated_word_count",
    "generic_substitution_count",
    "revision_marker_count",
    "incomplete_utterance_count",
    "syntactic_complexity_score",
    "retrieval_event_count",
}


def test_extract_disfluency_features_returns_expected_contract():
    features = extract_disfluency_features("The boy is stealing cookies from the jar.")

    assert set(features.keys()) == _EXPECTED_KEYS
    assert all(isinstance(v, float) for v in features.values())


def test_repeated_word_count_detects_immediate_repeats():
    features = extract_disfluency_features("the the boy is is running")

    assert features["repeated_word_count"] == 2.0


def test_generic_substitution_count_detects_vague_words():
    features = extract_disfluency_features("he was doing that thing with the stuff over there")

    assert features["generic_substitution_count"] == 2.0


def test_revision_marker_count_detects_markers():
    features = extract_disfluency_features("the jar, I mean, the cookie jar on the shelf")

    assert features["revision_marker_count"] == 1.0


def test_incomplete_utterance_count_flags_trailing_fragment():
    complete = extract_disfluency_features("This is a complete sentence.")
    incomplete = extract_disfluency_features("This sentence just trails off without")

    assert complete["incomplete_utterance_count"] == 0.0
    assert incomplete["incomplete_utterance_count"] == 1.0


def test_syntactic_complexity_increases_with_conjunctions():
    simple = extract_disfluency_features("The boy runs. The girl jumps.")
    complex_ = extract_disfluency_features("The boy runs because the girl jumps while the dog barks.")

    assert complex_["syntactic_complexity_score"] > simple["syntactic_complexity_score"]


def test_retrieval_event_count_zero_without_segments():
    features = extract_disfluency_features("um the boy is running")

    assert features["retrieval_event_count"] == 0.0


def test_retrieval_event_count_detects_filler_before_long_gap():
    segments = [
        {
            "text": "um the boy",
            "words": [
                {"word": "um", "start": 0.0, "end": 0.3, "probability": 0.9},
                {"word": "the", "start": 1.3, "end": 1.5, "probability": 0.9},
                {"word": "boy", "start": 1.5, "end": 1.8, "probability": 0.9},
            ],
        }
    ]

    features = extract_disfluency_features("um the boy", segments=segments)

    assert features["retrieval_event_count"] == 1.0
