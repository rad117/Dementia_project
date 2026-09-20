"""ASR (speech-to-text) transcription -- the layer above acoustic features.

Accepts either a path to a real dataset .wav file, or raw bytes of an
uploaded recording (same input shapes as ml/features/acoustic.py). Uses
faster-whisper (ctranslate2-based, no torch dependency) for CPU-friendly
transcription. Returns raw transcript text plus basic ASR-derived metadata
only -- NOT semantic/linguistic features (vocabulary richness, coherence,
concept coverage, etc.), which belong to the future ml/nlp/ layer.

The current dataset is confirmed English-only (project supervisor,
2026-09-20), so callers default to language="en" and the lightweight
"small.en" checkpoint. Both are explicit parameters, not hardcoded, so a
future multilingual dataset only needs a different language code and a
multilingual checkpoint (e.g. "small") at the call site -- no interface
change.
"""

import io
from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

_model_cache: dict[str, WhisperModel] = {}
_cache_lock = Lock()


class TranscriptionError(Exception):
    """Raised when audio cannot be decoded or transcribed."""


def _get_model(model_size: str) -> WhisperModel:
    if model_size in _model_cache:
        return _model_cache[model_size]
    with _cache_lock:
        if model_size not in _model_cache:
            _model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
        return _model_cache[model_size]


def _serialize_words(segment) -> list[dict]:
    words = getattr(segment, "words", None) or []
    return [
        {
            "word": w.word.strip(),
            "start": float(w.start),
            "end": float(w.end),
            "probability": float(w.probability),
        }
        for w in words
    ]


def transcribe(audio: str | Path | bytes, *, language: str = "en", model_size: str = "small.en") -> dict:
    """Transcribes audio and returns a flat dict of ASR-layer fields.

    Returns {"transcript_text", "word_count", "avg_logprob",
    "no_speech_prob", "duration_seconds", "segments", "detected_language",
    "detected_language_probability"}. "segments" carries per-word
    timestamps/confidence (word_timestamps=True) -- consumed by the
    NLP/disfluency and pronunciation-proxy layers, not by the acoustic
    model's own feature vector. Raises TranscriptionError on
    unreadable/corrupt audio or an unsupported input type.
    """
    if isinstance(audio, (str, Path)):
        source = str(audio)
    elif isinstance(audio, bytes):
        source = io.BytesIO(audio)
    else:
        raise TranscriptionError(f"Unsupported audio input type: {type(audio)!r}")

    try:
        model = _get_model(model_size)
        segments, info = model.transcribe(source, language=language, word_timestamps=True)
        segments = list(segments)
    except Exception as exc:
        raise TranscriptionError(f"Could not transcribe audio: {exc}") from exc

    detected_language = getattr(info, "language", language) if info is not None else language
    detected_language_probability = float(getattr(info, "language_probability", 1.0)) if info is not None else 1.0

    if not segments:
        return {
            "transcript_text": "",
            "word_count": 0,
            "avg_logprob": 0.0,
            "no_speech_prob": 1.0,
            "duration_seconds": float(info.duration) if info is not None else 0.0,
            "segments": [],
            "detected_language": detected_language,
            "detected_language_probability": detected_language_probability,
        }

    transcript_text = " ".join(segment.text.strip() for segment in segments).strip()
    avg_logprob = sum(segment.avg_logprob for segment in segments) / len(segments)
    no_speech_prob = sum(getattr(segment, "no_speech_prob", 0.0) for segment in segments) / len(segments)

    return {
        "transcript_text": transcript_text,
        "word_count": len(transcript_text.split()),
        "avg_logprob": float(avg_logprob),
        "no_speech_prob": float(no_speech_prob),
        "duration_seconds": float(info.duration),
        "segments": [
            {
                "text": segment.text.strip(),
                "start": float(segment.start),
                "end": float(segment.end),
                "avg_logprob": float(segment.avg_logprob),
                "words": _serialize_words(segment),
            }
            for segment in segments
        ],
        "detected_language": detected_language,
        "detected_language_probability": detected_language_probability,
    }
