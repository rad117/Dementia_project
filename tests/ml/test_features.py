import io

import av
import numpy as np
import pytest
import soundfile as sf

from ml.features.acoustic import AudioProcessingError, extract_features

_EXPECTED_KEYS = {
    "duration_seconds",
    "pause_count",
    "total_pause_duration_seconds",
    "pause_ratio",
    "voiced_rate_per_min",
    "longest_pause_seconds",
    "first_speech_onset_seconds",
    "pitch_mean_hz",
    "pitch_std_hz",
    "voice_breaks_count",
    "energy_rms_mean",
    "energy_rms_std",
    *(f"mfcc_{i}_mean" for i in range(1, 14)),
    *(f"mfcc_{i}_std" for i in range(1, 14)),
    "jitter_percent",
    "shimmer_percent",
    "hnr_db",
    "spectral_centroid_hz_mean",
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


def test_extract_features_from_path(tmp_path):
    samples, sr = _sine_wave()
    wav_path = tmp_path / "tone.wav"
    sf.write(str(wav_path), samples, sr)

    features = extract_features(wav_path)

    assert set(features.keys()) == _EXPECTED_KEYS
    assert features["duration_seconds"] == pytest.approx(1.0, abs=0.05)
    assert all(np.isfinite(v) for v in features.values())


def test_extract_features_from_wav_bytes_matches_path(tmp_path):
    samples, sr = _sine_wave()
    wav_path = tmp_path / "tone.wav"
    sf.write(str(wav_path), samples, sr)
    wav_bytes = wav_path.read_bytes()

    from_path = extract_features(wav_path)
    from_bytes = extract_features(wav_bytes)

    assert set(from_path.keys()) == set(from_bytes.keys()) == _EXPECTED_KEYS
    assert from_bytes["duration_seconds"] == pytest.approx(from_path["duration_seconds"], abs=0.05)


def test_extract_features_from_webm_opus_bytes():
    samples, sr = _sine_wave(sr=48000)
    webm_bytes = _write_webm_opus_bytes(samples, sr)

    features = extract_features(webm_bytes)

    assert set(features.keys()) == _EXPECTED_KEYS
    assert features["duration_seconds"] == pytest.approx(1.0, abs=0.1)
    assert all(np.isfinite(v) for v in features.values())


def test_voice_quality_features_are_plausible_for_clean_tone(tmp_path):
    # A clean sine tone should read as near-perfect voice quality: very low
    # jitter/shimmer, high HNR, no voice breaks -- a sanity check on the
    # parselmouth wiring rather than an assertion on exact values.
    samples, sr = _sine_wave(seconds=2.0, freq=150.0)
    wav_path = tmp_path / "tone.wav"
    sf.write(str(wav_path), samples, sr)

    features = extract_features(wav_path)

    assert features["jitter_percent"] < 1.0
    assert features["shimmer_percent"] < 1.0
    assert features["hnr_db"] > 20.0
    assert features["voice_breaks_count"] == 0.0


def test_extract_features_raises_on_corrupt_bytes():
    with pytest.raises(AudioProcessingError):
        extract_features(b"not a real audio file, just garbage bytes")


def test_extract_features_raises_on_too_short_audio():
    samples = np.zeros(10, dtype="float32")  # far under 0.1s at any real sample rate
    buf = io.BytesIO()
    sf.write(buf, samples, 16000, format="WAV")
    with pytest.raises(AudioProcessingError):
        extract_features(buf.getvalue())


def test_extract_features_raises_on_unsupported_type():
    with pytest.raises(AudioProcessingError):
        extract_features(12345)
