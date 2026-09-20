from pathlib import Path

import pytest

from ml.nlp.linguistic import LinguisticFeatureError, extract_linguistic_features

_EXPECTED_KEYS = {
    "word_count",
    "unique_word_count",
    "type_token_ratio",
    "mean_word_length",
    "sentence_count",
    "words_per_sentence",
    "pronoun_ratio",
    "filler_word_count",
    "filler_word_ratio",
    "repeated_bigram_ratio",
    "cookie_theft_concept_count",
    "cookie_theft_concept_ratio",
    "mean_adjacent_sentence_similarity",
}


def test_extract_linguistic_features_returns_expected_contract():
    text = "The boy is stealing cookies from the cookie jar. The sink is overflowing with water."

    features = extract_linguistic_features(text)

    assert set(features.keys()) == _EXPECTED_KEYS
    assert features["word_count"] == 15
    assert features["sentence_count"] == 2
    assert all(isinstance(v, (int, float)) for v in features.values())


def test_extract_linguistic_features_raises_on_empty_transcript():
    with pytest.raises(LinguisticFeatureError):
        extract_linguistic_features("")


def test_extract_linguistic_features_raises_on_whitespace_only():
    with pytest.raises(LinguisticFeatureError):
        extract_linguistic_features("   \n\t  ")


def test_type_token_ratio_is_one_for_all_unique_words():
    features = extract_linguistic_features("apple banana cherry date")

    assert features["type_token_ratio"] == pytest.approx(1.0)
    assert features["unique_word_count"] == 4


def test_type_token_ratio_drops_with_repetition():
    features = extract_linguistic_features("cookie cookie cookie cookie")

    assert features["type_token_ratio"] == pytest.approx(0.25)
    assert features["unique_word_count"] == 1


def test_pronoun_ratio_counts_known_pronouns():
    features = extract_linguistic_features("he took it and she saw them")

    # he, it, she, them -> 4 pronouns out of 7 words
    assert features["pronoun_ratio"] == pytest.approx(4 / 7)


def test_filler_word_ratio_counts_fillers():
    features = extract_linguistic_features("um the boy uh is running")

    assert features["filler_word_count"] == 2.0
    assert features["filler_word_ratio"] == pytest.approx(2 / 6)


def test_repeated_bigram_ratio_detects_repetition():
    features = extract_linguistic_features("the boy the boy is running fast")

    assert features["repeated_bigram_ratio"] > 0.0


def test_repeated_bigram_ratio_zero_when_no_repeats():
    features = extract_linguistic_features("a completely unique sentence with no repeats")

    assert features["repeated_bigram_ratio"] == pytest.approx(0.0)


def test_cookie_theft_concept_coverage_detects_known_concepts():
    text = "The boy and girl are near the cookie jar by the sink, which is overflowing."

    features = extract_linguistic_features(text)

    # boy, girl, cookie, jar, sink, overflow -> at least 6 of 15 concepts
    assert features["cookie_theft_concept_count"] >= 6.0
    assert 0.0 < features["cookie_theft_concept_ratio"] <= 1.0


def test_cookie_theft_concept_coverage_zero_for_unrelated_text():
    features = extract_linguistic_features("quantum physics involves subatomic particles")

    assert features["cookie_theft_concept_count"] == 0.0
    assert features["cookie_theft_concept_ratio"] == pytest.approx(0.0)


def test_single_sentence_has_zero_coherence():
    features = extract_linguistic_features("just one sentence here")

    assert features["sentence_count"] == 1
    assert features["mean_adjacent_sentence_similarity"] == pytest.approx(0.0)


def test_words_per_sentence_matches_manual_calc():
    features = extract_linguistic_features("one two three. four five six seven.")

    assert features["words_per_sentence"] == pytest.approx(3.5)


_transcript_cache_path = Path("data/adresso2021_transcripts_cache.csv")


@pytest.mark.skipif(
    not _transcript_cache_path.exists(),
    reason="real ASR transcript cache not present locally",
)
def test_real_transcript_from_cache_produces_finite_features():
    import pandas as pd

    df = pd.read_csv(_transcript_cache_path)
    text = str(df.iloc[0]["transcript_text"])

    features = extract_linguistic_features(text)

    assert set(features.keys()) == _EXPECTED_KEYS
    assert all(v == v for v in features.values())  # no NaNs
