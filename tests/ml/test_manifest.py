import numpy as np
import soundfile as sf

from ml.preprocessing.manifest import audit_report, build_manifest, parse_filename


def test_parse_filename_plain():
    result = parse_filename("adrso024")
    assert result == {"participant_id": "adrso024", "instructor_removed": False, "severity": None}


def test_parse_filename_underscore_i_suffix():
    result = parse_filename("adrso036_i")
    assert result == {"participant_id": "adrso036", "instructor_removed": True, "severity": None}


def test_parse_filename_hyphen_i_suffix():
    result = parse_filename("adrso025-i")
    assert result == {"participant_id": "adrso025", "instructor_removed": True, "severity": None}


def test_parse_filename_severe_suffix():
    result = parse_filename("adrso078_severe")
    assert result == {"participant_id": "adrso078", "instructor_removed": False, "severity": "severe"}


def _write_tiny_wav(path, seconds=1.0, sr=16000):
    samples = np.zeros(int(seconds * sr), dtype="float32")
    sf.write(str(path), samples, sr)


def test_build_manifest_walks_both_label_dirs(tmp_path):
    dementia_dir = tmp_path / "Dementia"
    normal_dir = tmp_path / "Normal"
    dementia_dir.mkdir()
    normal_dir.mkdir()
    _write_tiny_wav(dementia_dir / "adrso001_i.wav")
    _write_tiny_wav(dementia_dir / "adrso002_severe.wav")
    _write_tiny_wav(normal_dir / "adrso003.wav")

    manifest = build_manifest(tmp_path)

    assert len(manifest) == 3
    assert set(manifest["label"]) == {"Dementia", "Normal"}
    dementia_rows = manifest[manifest["label"] == "Dementia"].set_index("participant_id")
    assert bool(dementia_rows.loc["adrso001", "instructor_removed"]) is True
    assert dementia_rows.loc["adrso002", "severity"] == "severe"
    normal_row = manifest[manifest["label"] == "Normal"].iloc[0]
    assert normal_row["label_binary"] == 0
    assert normal_row["duration_seconds"] > 0
    assert normal_row["sample_rate"] == 16000


def test_audit_report_has_no_participant_level_columns(tmp_path):
    dementia_dir = tmp_path / "Dementia"
    normal_dir = tmp_path / "Normal"
    dementia_dir.mkdir()
    normal_dir.mkdir()
    _write_tiny_wav(dementia_dir / "adrso001_i.wav")
    _write_tiny_wav(normal_dir / "adrso002.wav")

    manifest = build_manifest(tmp_path)
    report = audit_report(manifest)

    assert report["n_files"] == 2
    assert report["class_counts"] == {"Dementia": 1, "Normal": 1}
    assert "participant_id" not in report
    assert "filepath" not in report
