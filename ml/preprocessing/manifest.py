"""Builds a dataset manifest from the raw ADReSSo-style audio folders.

Filename suffix meanings were confirmed by the project supervisor
(2026-09-20): `-i`/`_i` means the interviewer's voice was edited out of the
recording (a preprocessing confound for silence/pause-based features, not
just a naming curiosity); `_severe` means a confirmed severe-dementia case
(a single data point — not a basis for any severity model). See CONTEXT.md
Section 12.
"""

import re
from pathlib import Path

import pandas as pd
import soundfile as sf

_FILENAME_RE = re.compile(r"^(?P<participant_id>adrso\d+)(?P<suffix>_i|-i|_severe)?$")

_LABEL_DIRS = {"Dementia": 1, "Normal": 0}


def parse_filename(stem: str) -> dict:
    """Parses a filename stem (no extension) into its participant id and
    filename-encoded metadata. Raises ValueError on an unrecognized shape."""
    match = _FILENAME_RE.match(stem)
    if match is None:
        raise ValueError(f"Unrecognized filename stem: {stem!r}")
    suffix = match.group("suffix")
    return {
        "participant_id": match.group("participant_id"),
        "instructor_removed": suffix in ("_i", "-i"),
        "severity": "severe" if suffix == "_severe" else None,
    }


def build_manifest(data_root: Path = Path("data/adresso2021")) -> pd.DataFrame:
    """Walks Dementia/ and Normal/ under data_root and returns one row per
    .wav file: participant_id, filepath, label, label_binary,
    instructor_removed, severity, duration_seconds, sample_rate."""
    data_root = Path(data_root)
    rows = []
    for label, label_binary in _LABEL_DIRS.items():
        label_dir = data_root / label
        if not label_dir.is_dir():
            continue
        for wav_path in sorted(label_dir.glob("*.wav")):
            parsed = parse_filename(wav_path.stem)
            info = sf.info(str(wav_path))
            rows.append(
                {
                    "participant_id": parsed["participant_id"],
                    "filepath": wav_path.as_posix(),
                    "label": label,
                    "label_binary": label_binary,
                    "instructor_removed": parsed["instructor_removed"],
                    "severity": parsed["severity"],
                    "duration_seconds": info.duration,
                    "sample_rate": info.samplerate,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "participant_id",
            "filepath",
            "label",
            "label_binary",
            "instructor_removed",
            "severity",
            "duration_seconds",
            "sample_rate",
        ],
    )


def audit_report(manifest: pd.DataFrame) -> dict:
    """Aggregate-only stats safe to commit (no participant_id/filepath rows,
    which would otherwise leak a participant->diagnosis mapping)."""
    return {
        "n_files": len(manifest),
        "class_counts": manifest["label"].value_counts().to_dict(),
        "duration_seconds": {
            "min": manifest["duration_seconds"].min(),
            "max": manifest["duration_seconds"].max(),
            "mean": manifest["duration_seconds"].mean(),
            "median": manifest["duration_seconds"].median(),
        },
        "sample_rate_counts": manifest["sample_rate"].value_counts().to_dict(),
        "instructor_removed_by_label": (
            manifest.groupby("label")["instructor_removed"].sum().to_dict()
        ),
        "severity_counts": manifest["severity"].value_counts(dropna=False).to_dict(),
    }
