"""Disfluency/production heuristics layered on top of ml/nlp/linguistic.py.

Kept in a sibling module rather than folded into linguistic.py because
these are annotation-style heuristics (rule-based lexicon/marker matching,
some genuinely low-confidence) distinct from linguistic.py's vetted,
already-model-trained lexical/fluency metrics -- none of these feed
feature_names.json, so changing them never requires retraining.

Several of these are explicitly weak proxies, not clinical measures:
- revision_marker_count relies on ASR punctuation/disfluency markup, which
  is rarely preserved cleanly in transcripts.
- retrieval_event_count is a cross-modal heuristic (filler immediately
  before a long word-to-word gap) that has not been validated against
  real recordings -- flagged for manual QA, not just unit tests.
- incomplete_utterance_count only catches a trailing unterminated
  fragment, not genuinely abandoned mid-sentence utterances.
"""

from ml.nlp.linguistic import _FILLER_WORDS, _SENTENCE_SPLIT_RE, _split_sentences, _tokenize

_GENERIC_WORDS = {
    "thing", "things", "stuff", "something", "somewhere", "someone",
    "whatever", "whatchamacallit", "thingy", "stuffs",
}
_REVISION_MARKERS = ("i mean", "sorry", "no wait", "or rather", "that is")
_CONJUNCTIONS = {
    "and", "but", "or", "because", "since", "although", "though", "while",
    "if", "when", "after", "before", "so", "that", "which", "who",
}

# Gap (seconds) between consecutive ASR words after a filler that we treat
# as a possible word-retrieval pause -- a threshold chosen to be well
# above normal fluent-speech micro-pauses, not calibrated against labeled data.
_RETRIEVAL_GAP_THRESHOLD_SECONDS = 0.8


def _repeated_word_count(words: list[str]) -> float:
    return float(sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1]))


def _generic_substitution_count(words: list[str]) -> float:
    return float(sum(1 for w in words if w in _GENERIC_WORDS))


def _revision_marker_count(text: str) -> float:
    lowered = text.lower()
    return float(sum(lowered.count(marker) for marker in _REVISION_MARKERS))


def _incomplete_utterance_count(text: str) -> float:
    trailing = _SENTENCE_SPLIT_RE.split(text.strip())
    return 1.0 if trailing and trailing[-1].strip() else 0.0


def _syntactic_complexity_score(words: list[str], sentence_count: int) -> float:
    conjunction_count = sum(1 for w in words if w in _CONJUNCTIONS)
    return conjunction_count / sentence_count if sentence_count else 0.0


def _retrieval_event_count(segments: list[dict] | None) -> float:
    if not segments:
        return 0.0
    flat_words = [w for segment in segments for w in segment.get("words", [])]
    count = 0
    for i, word in enumerate(flat_words[:-1]):
        if word["word"].strip(".,!?").lower() not in _FILLER_WORDS:
            continue
        gap = flat_words[i + 1]["start"] - word["end"]
        if gap >= _RETRIEVAL_GAP_THRESHOLD_SECONDS:
            count += 1
    return float(count)


def extract_disfluency_features(transcript_text: str, segments: list[dict] | None = None) -> dict:
    """Returns a flat dict of scalar disfluency/heuristic features.
    Safe to call on any non-empty transcript_text; segments is optional
    (only retrieval_event_count needs word-level timestamps)."""
    words = _tokenize(transcript_text)
    sentences = _split_sentences(transcript_text)

    return {
        "repeated_word_count": _repeated_word_count(words),
        "generic_substitution_count": _generic_substitution_count(words),
        "revision_marker_count": _revision_marker_count(transcript_text),
        "incomplete_utterance_count": _incomplete_utterance_count(transcript_text),
        "syntactic_complexity_score": _syntactic_complexity_score(words, len(sentences)),
        "retrieval_event_count": _retrieval_event_count(segments),
    }
