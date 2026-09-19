from backend.db import create_assessment_row, get_assessment_row, init_db, save_result_row


def test_create_then_get_returns_pending_row(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    create_assessment_row("a1", "patient-1", "en", "cookie-theft", db_path=db_path)
    row = get_assessment_row("a1", db_path=db_path)

    assert row["id"] == "a1"
    assert row["patient_id"] == "patient-1"
    assert row["language"] == "en"
    assert row["task_id"] == "cookie-theft"
    assert row["status"] == "pending_recording"
    assert row["risk_score"] is None
    assert row["completed_at"] is None


def test_save_result_row_updates_status_and_fields(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    create_assessment_row("a2", "patient-2", "en", "cookie-theft", db_path=db_path)

    save_result_row(
        "a2",
        risk_score=0.73,
        speech_features={"duration_seconds": 12.0},
        linguistic_features={},
        model_version="baseline-rf-v1",
        needs_clinician_review=True,
        db_path=db_path,
    )
    row = get_assessment_row("a2", db_path=db_path)

    assert row["status"] == "complete"
    assert row["risk_score"] == 0.73
    assert row["model_version"] == "baseline-rf-v1"
    assert bool(row["needs_clinician_review"]) is True
    assert row["completed_at"] is not None


def test_get_assessment_row_returns_none_for_unknown_id(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    assert get_assessment_row("does-not-exist", db_path=db_path) is None
