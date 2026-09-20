"""SQLite persistence for assessments -- one table, no relations yet.

Plain stdlib sqlite3, not an ORM: single table, no migrations needed,
matches the repo's existing "plain requirements.txt, no pyproject.toml"
simplicity convention. Each function opens/closes its own connection per
call, avoiding check_same_thread pitfalls at this project's concurrency
scale.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "assessments.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    language TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_recording',
    risk_score REAL,
    speech_features TEXT,
    linguistic_features TEXT,
    semantic_features TEXT,
    production_features TEXT,
    quality_signals TEXT,
    transcript TEXT,
    raw_features TEXT,
    model_version TEXT,
    needs_clinician_review INTEGER,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
"""


def init_db(db_path: Path | None = None) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(_SCHEMA)


def create_assessment_row(
    assessment_id: str,
    patient_id: str,
    language: str,
    task_id: str,
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            "INSERT INTO assessments (id, patient_id, language, task_id, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending_recording', ?)",
            (assessment_id, patient_id, language, task_id, datetime.now(UTC).isoformat()),
        )


def get_assessment_row(assessment_id: str, db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()
        return dict(row) if row is not None else None


def list_assessments_by_patient(patient_id: str, db_path: Path | None = None) -> list[dict]:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM assessments WHERE patient_id = ? AND status = 'complete' "
            "ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def save_result_row(
    assessment_id: str,
    *,
    risk_score: float,
    speech_features: dict,
    linguistic_features: dict,
    semantic_features: dict,
    production_features: dict,
    quality_signals: dict,
    transcript: dict | None,
    raw_features: dict,
    model_version: str,
    needs_clinician_review: bool,
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            """
            UPDATE assessments
            SET status = 'complete',
                risk_score = ?,
                speech_features = ?,
                linguistic_features = ?,
                semantic_features = ?,
                production_features = ?,
                quality_signals = ?,
                transcript = ?,
                raw_features = ?,
                model_version = ?,
                needs_clinician_review = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                risk_score,
                json.dumps(speech_features),
                json.dumps(linguistic_features),
                json.dumps(semantic_features),
                json.dumps(production_features),
                json.dumps(quality_signals),
                json.dumps(transcript) if transcript is not None else None,
                json.dumps(raw_features),
                model_version,
                int(needs_clinician_review),
                datetime.now(UTC).isoformat(),
                assessment_id,
            ),
        )
