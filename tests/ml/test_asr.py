import io
from pathlib import Path

import av
import numpy as np
import pytest
import soundfile as sf

from ml.asr import transcribe as transcribe_module
from ml.asr.transcribe import TranscriptionError, transcribe
from ml.preprocessing.manifest import build_manifest

_EXPECTED_KEYS = {
    "transcript_text",
    "word_count",
    "avg_logprob",
    "no_speech_prob",
    "duration_seconds",
    "segments",
    "detected_language",
    "detected_language_probability",
}


def _sine_wave(seconds=1.0, sr=16000, freq=220.0):
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype("float32"), sr


def _write_wav_bytes(samples, sr):
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    return buf.getvalue()


def _write_webm_opus_bytes(samples, sr):
    buf = io.BytesIO()
    container = av.open(buf, mode="w", format="webm")
    stream = container.add_stream("libopus", rate=sr)
    frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="fltp", layout="mono")
    frame.sample_rate = sr
    frame.pts = 0
    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()
    return buf.getvalue()


class _FakeWord:
    def __init__(self, word, start, end, probability=0.95):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability


class _FakeSegment:
    def __init__(self, text, avg_logprob=-0.2, no_speech_prob=0.05, start=0.0, end=1.0, words=None):
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob
        self.start = start
        self.end = end
        self.words = words


class _FakeInfo:
    def __init__(self, duration, language="en", language_probability=1.0):
        self.duration = duration
        self.language = language
        self.language_probability = language_probability


class _FakeModel:
    def __init__(self, segments=None, duration=1.0):
        self._segments = segments if segments is not None else [_FakeSegment("hello world")]
        self._duration = duration

    def transcribe(self, source, language=None, word_timestamps=None):
        return iter(self._segments), _FakeInfo(self._duration)


@pytest.fixture(autouse=True)
def _clear_model_cache():
    transcribe_module._model_cache.clear()
    yield
    transcribe_module._model_cache.clear()


def _use_fake_model(monkeypatch, model):
    monkeypatch.setattr(transcribe_module, "_get_model", lambda model_size: model)


def test_transcribe_from_path_returns_expected_contract(monkeypatch, tmp_path):
    _use_fake_model(monkeypatch, _FakeModel([_FakeSegment("the boy is stealing cookies")], duration=2.5))
    samples, sr = _sine_wave()
    wav_path = tmp_path / "tone.wav"
    sf.write(str(wav_path), samples, sr)

    result = transcribe(wav_path)

    assert set(result.keys()) == _EXPECTED_KEYS
    assert result["transcript_text"] == "the boy is stealing cookies"
    assert result["word_count"] == 5
    assert result["duration_seconds"] == pytest.approx(2.5)
    assert isinstance(result["avg_logprob"], float)
    assert isinstance(result["no_speech_prob"], float)


def test_transcribe_from_wav_bytes(monkeypatch):
    _use_fake_model(monkeypatch, _FakeModel([_FakeSegment("hello")]))
    samples, sr = _sine_wave()
    wav_bytes = _write_wav_bytes(samples, sr)

    result = transcribe(wav_bytes)

    assert result["transcript_text"] == "hello"
    assert result["word_count"] == 1


def test_transcribe_from_webm_opus_bytes(monkeypatch):
    _use_fake_model(monkeypatch, _FakeModel([_FakeSegment("hello there")]))
    samples, sr = _sine_wave(sr=48000)
    webm_bytes = _write_webm_opus_bytes(samples, sr)

    result = transcribe(webm_bytes)

    assert result["transcript_text"] == "hello there"


def test_transcribe_joins_multiple_segments(monkeypatch):
    segments = [_FakeSegment("first part."), _FakeSegment("second part.")]
    _use_fake_model(monkeypatch, _FakeModel(segments))

    result = transcribe(b"irrelevant, model is faked")

    assert result["transcript_text"] == "first part. second part."


def test_transcribe_handles_no_speech(monkeypatch):
    _use_fake_model(monkeypatch, _FakeModel([], duration=3.0))

    result = transcribe(b"irrelevant, model is faked")

    assert result["transcript_text"] == ""
    assert result["word_count"] == 0
    assert result["no_speech_prob"] == 1.0
    assert result["duration_seconds"] == pytest.approx(3.0)


def test_transcribe_returns_word_level_timestamps(monkeypatch):
    words = [_FakeWord("hello", 0.0, 0.4, 0.98), _FakeWord("world", 0.4, 0.9, 0.91)]
    segment = _FakeSegment("hello world", start=0.0, end=0.9, words=words)
    _use_fake_model(monkeypatch, _FakeModel([segment], duration=0.9))

    result = transcribe(b"irrelevant, model is faked")

    assert len(result["segments"]) == 1
    seg = result["segments"][0]
    assert seg["text"] == "hello world"
    assert seg["start"] == pytest.approx(0.0)
    assert seg["end"] == pytest.approx(0.9)
    assert [w["word"] for w in seg["words"]] == ["hello", "world"]
    assert seg["words"][1]["probability"] == pytest.approx(0.91)
    assert result["detected_language"] == "en"
    assert result["detected_language_probability"] == pytest.approx(1.0)


def test_transcribe_raises_on_unsupported_type(monkeypatch):
    _use_fake_model(monkeypatch, _FakeModel())
    with pytest.raises(TranscriptionError):
        transcribe(12345)


def test_transcribe_wraps_model_errors(monkeypatch):
    class _BrokenModel:
        def transcribe(self, source, language=None, word_timestamps=None):
            raise RuntimeError("decode failed")

    _use_fake_model(monkeypatch, _BrokenModel())
    with pytest.raises(TranscriptionError):
        transcribe(b"garbage bytes")


def test_transcribe_passes_language_through(monkeypatch):
    seen = {}

    class _RecordingModel:
        def transcribe(self, source, language=None, word_timestamps=None):
            seen["language"] = language
            return iter([_FakeSegment("ok")]), _FakeInfo(1.0)

    _use_fake_model(monkeypatch, _RecordingModel())
    transcribe(b"irrelevant, model is faked", language="hi")

    assert seen["language"] == "hi"


pytestmark_real = pytest.mark.skipif(
    not Path("data/adresso2021").exists(),
    reason="real ADReSSo dataset not present locally",
)


@pytestmark_real
def test_transcribe_real_short_file_produces_nonempty_transcript():
    manifest = build_manifest()
    shortest = manifest.sort_values("duration_seconds").iloc[0]

    result = transcribe(Path(shortest["filepath"]))

    assert len(result["transcript_text"].strip()) > 0
    assert result["word_count"] > 0
