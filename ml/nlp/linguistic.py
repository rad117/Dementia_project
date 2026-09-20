"""NLP/semantic feature extraction -- the layer above ASR transcripts.

Takes the transcript text produced by ml/asr/transcribe.py and returns
lexical, fluency, and semantic-content features documented as the
"ASR/transcript" and "NLP/semantic" layers in CONTEXT.md Section 5:
vocabulary usage, repetitions, filler markers, concept coverage relative
to the Cookie Theft task, and coherence between sentences.

Deliberately dependency-light: no torch/transformers, no downloaded
embedding model. Coherence uses TF-IDF cosine similarity (scikit-learn,
already a project dependency) between consecutive sentences rather than a
neural sentence embedding -- a weaker but zero-new-dependency proxy,
consistent with this project's stance on heavy ML dependencies (see
ml/asr/transcribe.py's model-choice rationale). Revisit if evaluation
shows this proxy is too weak to be useful.

The Cookie Theft concept list is task-specific (CONTEXT.md's confirmed
task, 2026-09-20) -- these features are not meaningful for a different
picture-description task without updating _COOKIE_THEFT_CONCEPTS.
"""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_WORD_RE = re.compile(r"[a-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

_PRONOUNS = {
    "i", "me", "my", "mine", "you", "your", "yours", "he", "him", "his",
    "she", "her", "hers", "it", "its", "we", "us", "our", "ours",
    "they", "them", "their", "theirs", "this", "that", "these", "those",
    "someone", "somebody", "something", "anyone", "anybody", "anything",
}
_FILLER_WORDS = {"um", "umm", "uh", "uhh", "erm", "hmm"}

# Standard Cookie Theft picture-description content units (Croisile et al.
# 1996 / Giles et al. 1996 style information units), with common surface
# variants for simple substring-free word matching.
_COOKIE_THEFT_CONCEPTS = {
    "mother": {"mother", "mom", "woman", "lady", "housewife"},
    "boy": {"boy"},
    "girl": {"girl"},
    "stool": {"stool", "chair"},
    "cookie": {"cookie", "cookies"},
    "jar": {"jar"},
    "sink": {"sink"},
    "water": {"water"},
    "overflow": {"overflow", "overflowing", "overflowed", "spilling", "spill"},
    "dishes": {"dish", "dishes", "plate", "plates"},
    "curtain": {"curtain", "curtains"},
    "window": {"window"},
    "cupboard": {"cupboard", "cabinet", "shelf"},
    "faucet": {"faucet", "tap"},
    "floor": {"floor"},
}


class LinguisticFeatureError(Exception):
    """Raised when a transcript has no usable text to derive features from."""


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _repeated_bigram_ratio(words: list[str]) -> float:
    if len(words) < 2:
        return 0.0
    bigrams = list(zip(words, words[1:]))
    counts: dict[tuple[str, str], int] = {}
    for bg in bigrams:
        counts[bg] = counts.get(bg, 0) + 1
    repeated = sum(1 for bg in bigrams if counts[bg] > 1)
    return repeated / len(bigrams)


def _concept_coverage(words: set[str]) -> tuple[int, float]:
    matched = sum(1 for variants in _COOKIE_THEFT_CONCEPTS.values() if words & variants)
    total = len(_COOKIE_THEFT_CONCEPTS)
    return matched, matched / total


def _mean_adjacent_sentence_similarity(sentences: list[str]) -> float:
    if len(sentences) < 2:
        return 0.0
    try:
        vectors = TfidfVectorizer(stop_words="english").fit_transform(sentences)
    except ValueError:
        return 0.0  # e.g. every sentence is entirely stopwords
    sims = [
        cosine_similarity(vectors[i], vectors[i + 1])[0][0]
        for i in range(vectors.shape[0] - 1)
    ]
    return float(sum(sims) / len(sims))


def extract_linguistic_features(transcript_text: str) -> dict:
    """Returns a flat dict of scalar linguistic/semantic features.

    Raises LinguisticFeatureError if transcript_text is empty or has no
    recognizable words (e.g. an ASR no-speech result)."""
    words = _tokenize(transcript_text)
    if not words:
        raise LinguisticFeatureError("Transcript has no usable words")

    word_set = set(words)
    sentences = _split_sentences(transcript_text)
    filler_count = sum(1 for w in words if w in _FILLER_WORDS)
    pronoun_count = sum(1 for w in words if w in _PRONOUNS)
    concept_count, concept_ratio = _concept_coverage(word_set)

    return {
        "word_count": len(words),
        "unique_word_count": len(word_set),
        "type_token_ratio": len(word_set) / len(words),
        "mean_word_length": sum(len(w) for w in words) / len(words),
        "sentence_count": len(sentences),
        "words_per_sentence": len(words) / len(sentences) if sentences else float(len(words)),
        "pronoun_ratio": pronoun_count / len(words),
        "filler_word_count": float(filler_count),
        "filler_word_ratio": filler_count / len(words),
        "repeated_bigram_ratio": _repeated_bigram_ratio(words),
        "cookie_theft_concept_count": float(concept_count),
        "cookie_theft_concept_ratio": concept_ratio,
        "mean_adjacent_sentence_similarity": _mean_adjacent_sentence_similarity(sentences),
    }
