import pytest

from ml.nlp.linguistic import LinguisticFeatureError
from ml.nlp.semantic import extract_semantic_features

_EXPECTED_KEYS = {
    "concepts_identified",
    "concepts_expected",
    "concept_coverage",
    "semantic_relevance",
    "information_density",
    "coherence",
    "redundancy",
}


def test_extract_semantic_features_returns_expected_contract():
    text = "The boy and girl are near the cookie jar by the sink, which is overflowing."

    features = extract_semantic_features(text)

    assert set(features.keys()) == _EXPECTED_KEYS
    assert all(isinstance(v, float) for v in features.values())


def test_extract_semantic_features_raises_on_empty_transcript():
    with pytest.raises(LinguisticFeatureError):
        extract_semantic_features("")


def test_concept_coverage_matches_linguistic_concept_count():
    from ml.nlp.linguistic import extract_linguistic_features

    text = "The boy and girl are near the cookie jar by the sink, which is overflowing."
    semantic = extract_semantic_features(text)
    linguistic = extract_linguistic_features(text)

    assert semantic["concepts_identified"] == linguistic["cookie_theft_concept_count"]
    assert semantic["concept_coverage"] == pytest.approx(linguistic["cookie_theft_concept_ratio"])


def test_semantic_relevance_higher_for_on_topic_text():
    on_topic = "The mother is washing dishes at the sink while water overflows onto the floor."
    off_topic = "Quantum physics involves subatomic particles and wave functions."

    on_topic_relevance = extract_semantic_features(on_topic)["semantic_relevance"]
    off_topic_relevance = extract_semantic_features(off_topic)["semantic_relevance"]

    assert on_topic_relevance > off_topic_relevance


def test_information_density_drops_with_fillers_and_stopwords():
    dense = "boy girl mother cookie jar sink water overflow dishes curtain"
    sparse = "um the uh a is of um the uh a"

    dense_density = extract_semantic_features(dense)["information_density"]
    sparse_density = extract_semantic_features(sparse)["information_density"]

    assert dense_density > sparse_density
