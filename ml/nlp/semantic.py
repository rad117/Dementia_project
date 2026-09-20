"""Semantic/task-content presentation layer, above ml/nlp/linguistic.py.

Reuses linguistic.py's concept list and sentence-similarity/repetition
helpers rather than duplicating them -- linguistic.py's
cookie_theft_concept_count/ratio and repeated_bigram_ratio are load-bearing
feature_names.json columns for the trained model and must not be renamed
or changed there; this module only adds presentation-layer fields under
clinician-facing names, computed from the same underlying data.

Deliberately dependency-light, same stance as linguistic.py: semantic
relevance uses TF-IDF cosine similarity (scikit-learn, already a project
dependency) against a synthetic reference description built from the
concept list, not a neural sentence embedding -- adding
sentence-transformers/torch would break this project's established
no-torch precedent (see ml/asr/transcribe.py's model-choice rationale).
Revisit only if evaluation shows this proxy is too weak.
"""

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ml.nlp.linguistic import (
    _COOKIE_THEFT_CONCEPTS,
    _FILLER_WORDS,
    _concept_coverage,
    _mean_adjacent_sentence_similarity,
    _repeated_bigram_ratio,
    _split_sentences,
    _tokenize,
    LinguisticFeatureError,
)

_REFERENCE_DESCRIPTION = " ".join(sorted(variants)[0] for variants in _COOKIE_THEFT_CONCEPTS.values())


def _semantic_relevance(transcript_text: str) -> float:
    try:
        vectors = TfidfVectorizer(stop_words="english").fit_transform(
            [transcript_text, _REFERENCE_DESCRIPTION]
        )
    except ValueError:
        return 0.0
    return float(cosine_similarity(vectors[0], vectors[1])[0][0])


def _information_density(words: list[str]) -> float:
    if not words:
        return 0.0
    content_words = [w for w in words if w not in ENGLISH_STOP_WORDS and w not in _FILLER_WORDS]
    return len(content_words) / len(words)


def extract_semantic_features(transcript_text: str) -> dict:
    """Returns a flat dict of scalar semantic/task-content features.
    Raises LinguisticFeatureError if transcript_text has no usable words
    (mirrors ml/nlp/linguistic.py's contract, since both derive from the
    same transcript)."""
    words = _tokenize(transcript_text)
    if not words:
        raise LinguisticFeatureError("Transcript has no usable words")

    word_set = set(words)
    sentences = _split_sentences(transcript_text)
    concepts_identified, concept_ratio = _concept_coverage(word_set)
    concepts_expected = len(_COOKIE_THEFT_CONCEPTS)

    return {
        "concepts_identified": float(concepts_identified),
        "concepts_expected": float(concepts_expected),
        "concept_coverage": concept_ratio,
        "semantic_relevance": _semantic_relevance(transcript_text),
        "information_density": _information_density(words),
        "coherence": _mean_adjacent_sentence_similarity(sentences),
        "redundancy": _repeated_bigram_ratio(words),
    }
