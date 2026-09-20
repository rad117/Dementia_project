"""Acoustic feature extraction for the acoustics-only baseline.

Accepts either a path to a real dataset .wav file, or raw bytes of an
uploaded recording. Uploaded recordings come from the browser's
MediaRecorder API (frontend/src/hooks/useRecorder.js) with no forced mime
type, which produces WebM/Opus, not WAV -- `soundfile` cannot decode that
directly, so the bytes path falls back to PyAV (which bundles its own
decoder, no system ffmpeg install required) when soundfile fails.
"""

import io
from pathlib import Path

import av
import librosa
import numpy as np
import parselmouth
import soundfile as sf

_TARGET_SR = 16000
_N_MFCC = 13
_MIN_DURATION_SECONDS = 0.1
_PITCH_FMIN_HZ = 65.0
_PITCH_FMAX_HZ = 400.0
_SILENCE_TOP_DB = 30


class AudioProcessingError(Exception):
    """Raised when audio cannot be decoded, or is too short/empty to use."""


def _load_from_path(path, sample_rate):
    sr = sample_rate or _TARGET_SR
    y, sr = librosa.load(str(path), sr=sr, mono=True)
    return y, sr


def _decode_with_soundfile(raw_bytes, target_sr):
    data, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != target_sr:
        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
    return data.astype("float32")


def _decode_with_pyav(raw_bytes, target_sr):
    container = av.open(io.BytesIO(raw_bytes))
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=target_sr)
    chunks = []
    try:
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
    finally:
        container.close()
    if not chunks:
        raise AudioProcessingError("No decodable audio frames found")
    return np.concatenate(chunks).astype("float32")


def _load_from_bytes(raw_bytes, sample_rate):
    target_sr = sample_rate or _TARGET_SR
    try:
        y = _decode_with_soundfile(raw_bytes, target_sr)
        return y, target_sr
    except AudioProcessingError:
        raise
    except Exception:
        pass  # not a soundfile-readable container (e.g. WebM/Opus) -- fall back to PyAV
    try:
        y = _decode_with_pyav(raw_bytes, target_sr)
        return y, target_sr
    except Exception as exc:
        raise AudioProcessingError(f"Could not decode audio bytes: {exc}") from exc


def extract_features(audio: str | Path | bytes, *, sample_rate: int | None = None) -> dict:
    """Returns a flat dict of scalar float features. Raises
    AudioProcessingError on unreadable, corrupt, or too-short/empty audio."""
    if isinstance(audio, (str, Path)):
        try:
            y, sr = _load_from_path(audio, sample_rate)
        except Exception as exc:
            raise AudioProcessingError(f"Could not load audio file: {exc}") from exc
    elif isinstance(audio, bytes):
        y, sr = _load_from_bytes(audio, sample_rate)
    else:
        raise AudioProcessingError(f"Unsupported audio input type: {type(audio)!r}")

    duration_seconds = len(y) / sr if sr else 0.0
    if len(y) == 0 or duration_seconds < _MIN_DURATION_SECONDS or not np.all(np.isfinite(y)):
        raise AudioProcessingError("Audio is too short, empty, or contains invalid samples")

    features: dict = {"duration_seconds": float(duration_seconds)}
    features.update(_pause_features(y, sr, duration_seconds))
    features.update(_pitch_features(y, sr))
    features.update(_energy_features(y))
    features.update(_mfcc_features(y, sr))
    features.update(_voice_quality_features(y, sr))
    features.update(_spectral_features(y, sr))
    return features


def _pause_features(y: np.ndarray, sr: int, duration_seconds: float) -> dict:
    intervals = librosa.effects.split(y, top_db=_SILENCE_TOP_DB)
    if len(intervals) == 0:
        return {
            "pause_count": 0.0,
            "total_pause_duration_seconds": duration_seconds,
            "pause_ratio": 1.0,
            "voiced_rate_per_min": 0.0,
            "longest_pause_seconds": 0.0,
            "first_speech_onset_seconds": 0.0,
        }
    gaps = [
        (intervals[i + 1][0] - intervals[i][1]) / sr for i in range(len(intervals) - 1)
    ]
    total_pause_duration_seconds = float(sum(gaps))
    pause_ratio = total_pause_duration_seconds / duration_seconds if duration_seconds > 0 else 0.0
    voiced_rate_per_min = len(intervals) / (duration_seconds / 60) if duration_seconds > 0 else 0.0
    return {
        "pause_count": float(len(gaps)),
        "total_pause_duration_seconds": total_pause_duration_seconds,
        "pause_ratio": pause_ratio,
        "voiced_rate_per_min": voiced_rate_per_min,
        "longest_pause_seconds": float(max(gaps)) if gaps else 0.0,
        "first_speech_onset_seconds": float(intervals[0][0] / sr),
    }


def _pitch_features(y: np.ndarray, sr: int) -> dict:
    f0, voiced_flag, _voiced_prob = librosa.pyin(
        y, fmin=_PITCH_FMIN_HZ, fmax=_PITCH_FMAX_HZ, sr=sr
    )
    voiced_mask = voiced_flag.astype(bool) if voiced_flag is not None else np.zeros_like(f0, dtype=bool)
    voice_breaks_count = _count_voice_breaks(voiced_mask)
    voiced_f0 = f0[voiced_mask]
    voiced_f0 = voiced_f0[~np.isnan(voiced_f0)]
    if voiced_f0.size == 0:
        return {"pitch_mean_hz": 0.0, "pitch_std_hz": 0.0, "voice_breaks_count": voice_breaks_count}
    return {
        "pitch_mean_hz": float(np.mean(voiced_f0)),
        "pitch_std_hz": float(np.std(voiced_f0)),
        "voice_breaks_count": voice_breaks_count,
    }


def _count_voice_breaks(voiced_mask: np.ndarray) -> float:
    """Counts interior voiced->unvoiced transitions after speech has
    started, as a proxy for perceptible voice breaks -- excludes the
    single leading unvoiced->voiced transition into the first utterance,
    which isn't a "break" in ongoing phonation."""
    if voiced_mask.size == 0 or not voiced_mask.any():
        return 0.0
    first_voiced = int(np.argmax(voiced_mask))
    interior = voiced_mask[first_voiced:]
    transitions = np.diff(interior.astype(int))
    return float(np.sum(transitions == -1))


def _energy_features(y: np.ndarray) -> dict:
    rms = librosa.feature.rms(y=y)[0]
    return {
        "energy_rms_mean": float(np.mean(rms)),
        "energy_rms_std": float(np.std(rms)),
    }


def _mfcc_features(y: np.ndarray, sr: int) -> dict:
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=_N_MFCC)
    features = {}
    for i in range(_N_MFCC):
        features[f"mfcc_{i + 1}_mean"] = float(np.mean(mfcc[i]))
        features[f"mfcc_{i + 1}_std"] = float(np.std(mfcc[i]))
    return features


def _voice_quality_features(y: np.ndarray, sr: int) -> dict:
    """Jitter/shimmer/HNR via Praat's validated algorithms (no equivalent
    in librosa -- hand-rolling perturbation-quotient math from a raw pitch
    contour is error-prone next to Praat's decades-mature implementation).
    Falls back to zeros if the signal has too little voiced content for
    Praat to build a point process (e.g. near-silent or very short clips)
    rather than raising -- these are supplementary fields, not required
    for the trained model's feature vector."""
    try:
        sound = parselmouth.Sound(y.astype("float64"), sampling_frequency=sr)
        point_process = parselmouth.praat.call(
            sound, "To PointProcess (periodic, cc)", _PITCH_FMIN_HZ, _PITCH_FMAX_HZ
        )
        jitter_local = parselmouth.praat.call(
            point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3
        )
        shimmer_local = parselmouth.praat.call(
            [sound, point_process],
            "Get shimmer (local)",
            0, 0, 0.0001, 0.02, 1.3, 1.6,
        )
        harmonicity = sound.to_harmonicity_cc(minimum_pitch=_PITCH_FMIN_HZ)
        hnr_db = parselmouth.praat.call(harmonicity, "Get mean", 0, 0)
    except Exception:
        return {"jitter_percent": 0.0, "shimmer_percent": 0.0, "hnr_db": 0.0}

    def _clean(value):
        value = float(value)
        return value if np.isfinite(value) else 0.0

    return {
        "jitter_percent": _clean(jitter_local) * 100,
        "shimmer_percent": _clean(shimmer_local) * 100,
        "hnr_db": _clean(hnr_db),
    }


def _spectral_features(y: np.ndarray, sr: int) -> dict:
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    return {"spectral_centroid_hz_mean": float(np.mean(centroid))}
