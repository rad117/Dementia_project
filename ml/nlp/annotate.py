"""Transcript segment annotation -- tags each ASR segment for
TranscriptViewer.jsx's highlighting (filler/repetition/revision/concept/
normal), reusing linguistic.py's filler-word/concept lexicons and
disfluency.py's revision markers.

Coarse, rule-based, and explicitly flagged (see docs/plan) as needing a
manual QA pass against a handful of real transcribed recordings before
being trusted -- real ASR output on free-description speech is far
messier than clean hand-authored sentences (run-on segments, disfluencies
mid-segment, imperfect Whisper segment boundaries), and this only
classifies whole segments, not sub-segment spans.
"""

from ml.nlp.disfluency import _REVISION_MARKERS
from ml.nlp.linguistic import _COOKIE_THEFT_CONCEPTS, _FILLER_WORDS, _tokenize


def _leading_words(text: str, n: int = 3) -> str:
    return " ".join(_tokenize(text)[:n])


def _classify_segment(text: str, prev_text: str | None) -> tuple[str, str | None]:
    tokens = _tokenize(text)
    if tokens and all(t in _FILLER_WORDS for t in tokens):
        return "filler", None

    lowered = text.lower()
    if any(marker in lowered for marker in _REVISION_MARKERS):
        return "revision", None

    if prev_text:
        prev_lead = _leading_words(prev_text)
        if prev_lead and prev_lead == _leading_words(text):
            return "repetition", None

    token_set = set(tokens)
    for concept, variants in _COOKIE_THEFT_CONCEPTS.items():
        if token_set & variants:
            return "concept", concept

    return "normal", None


def annotate_transcript_segments(segments: list[dict]) -> list[dict]:
    """Takes ml.asr.transcribe.transcribe()'s "segments" list and returns
    tagged segments: [{id, startSec, endSec, text, type, concept?}],
    matching the shape frontend/src/components/clinical/TranscriptViewer.jsx
    already renders. id is a local index ("seg-0", ...) -- callers
    (backend/services/results_mapper.py) prefix it with the assessment id."""
    annotated = []
    prev_text = None
    for i, segment in enumerate(segments):
        seg_type, concept = _classify_segment(segment["text"], prev_text)
        entry = {
            "id": f"seg-{i}",
            "startSec": segment["start"],
            "endSec": segment["end"],
            "text": segment["text"],
            "type": seg_type,
        }
        if concept:
            entry["concept"] = concept
        annotated.append(entry)
        prev_text = segment["text"]
    return annotated
