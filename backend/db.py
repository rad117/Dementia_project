"""SQLite persistence for assessments -- one table, no relations yet.

Plain stdlib sqlite3, not an ORM: single table, no migrations needed,
matches the repo's existing "plain requirements.txt, no pyproject.toml"
simplicity convention. Each function opens/closes its own connection per
call, avoiding check_same_thread pitfalls at this project's concurrency
scale.
"""

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

# DB_PATH env var lets a deployed host (e.g. Render) point this at a
# persistent disk mount instead of the container's ephemeral filesystem.
DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).resolve().parent / "assessments.db")))

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

# Columns added after the table's initial creation -- kept in sync with
# _SCHEMA above by _sync_columns(). Only nullable/no-default columns belong
# here (SQLite's ALTER TABLE ADD COLUMN can't add a NOT NULL column without
# a default against a table that already has rows).
_ASSESSMENT_COLUMNS = {
    "risk_score": "REAL",
    "speech_features": "TEXT",
    "linguistic_features": "TEXT",
    "semantic_features": "TEXT",
    "production_features": "TEXT",
    "quality_signals": "TEXT",
    "transcript": "TEXT",
    "raw_features": "TEXT",
    "model_version": "TEXT",
    "needs_clinician_review": "INTEGER",
    "completed_at": "TEXT",
}

_PATIENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    login_code TEXT UNIQUE NOT NULL,
    preferred_language TEXT,
    age INTEGER,
    created_at TEXT NOT NULL
);
"""

_CLINICIANS_SCHEMA = """
CREATE TABLE IF NOT EXISTS clinicians (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Clinical Professional',
    created_at TEXT NOT NULL
);
"""

_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


class PatientNotFoundError(Exception):
    """Raised by create_assessment_row when patient_id doesn't exist in the
    patients table -- callers (routes) map this to a 404."""


def init_db(db_path: Path | None = None) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(_SCHEMA)
        conn.execute(_PATIENTS_SCHEMA)
        conn.execute(_CLINICIANS_SCHEMA)
        conn.execute(_SESSIONS_SCHEMA)
        _sync_columns(conn)


def _sync_columns(conn: sqlite3.Connection) -> None:
    """CREATE TABLE IF NOT EXISTS is a no-op against a table that already
    exists on an older schema -- an existing assessments.db predating a
    column addition (e.g. semantic_features/production_features/etc.) would
    otherwise silently keep the old schema forever and fail at write time.
    Adds any column present in _SCHEMA but missing from the live table."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(assessments)")}
    for name, coltype in _ASSESSMENT_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE assessments ADD COLUMN {name} {coltype}")


def create_assessment_row(
    assessment_id: str,
    patient_id: str,
    language: str,
    task_id: str,
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        exists = conn.execute(
            "SELECT 1 FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if exists is None:
            raise PatientNotFoundError(patient_id)
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


def list_all_assessments(
    status: str | None = "complete",
    needs_review: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[dict]:
    """Lists assessments across all patients, most recent first.

    Defaults to status='complete' -- mirrors list_assessments_by_patient's
    convention and avoids returning pending_recording rows whose
    quality/screening fields are None (which downstream response building
    requires to be populated).
    """
    query = "SELECT * FROM assessments WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if needs_review is not None:
        query += " AND needs_clinician_review = ?"
        params.append(int(needs_review))
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
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


# --- Patients -----------------------------------------------------------


def get_patient_row(patient_id: str, db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        return dict(row) if row is not None else None


def get_patient_by_login_code(login_code: str, db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM patients WHERE login_code = ?", (login_code,)
        ).fetchone()
        return dict(row) if row is not None else None


def create_patient_row(
    patient_id: str,
    name: str,
    login_code: str,
    preferred_language: str | None = None,
    age: int | None = None,
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO patients "
            "(id, name, login_code, preferred_language, age, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, name, login_code, preferred_language, age, datetime.now(UTC).isoformat()),
        )


def list_patients(
    query: str | None = None,
    language: str | None = None,
    needs_review: bool | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Every patient, each enriched with assessment_count and
    latest_assessment_row (the full most-recent-assessment row dict, or
    None if the patient has none yet -- callers pass this straight to
    backend.services.results_mapper.build_assessment_info() to get the
    same nested {task, quality, screening, ...} shape used everywhere
    else, rather than this module re-deriving a partial version of it).

    Filtering by the enriched (computed) fields is simpler done in Python
    than in raw SQL here -- this table is small (demo/research-tool
    scale), so no join/window-function SQL is needed to keep it fast.
    """
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        patients = [dict(row) for row in conn.execute("SELECT * FROM patients").fetchall()]
        assessment_rows = conn.execute(
            "SELECT * FROM assessments WHERE status = 'complete' ORDER BY created_at DESC"
        ).fetchall()

    latest_by_patient: dict[str, dict] = {}
    count_by_patient: dict[str, int] = {}
    for row in assessment_rows:
        pid = row["patient_id"]
        count_by_patient[pid] = count_by_patient.get(pid, 0) + 1
        if pid not in latest_by_patient:
            latest_by_patient[pid] = dict(row)

    results = []
    for patient in patients:
        pid = patient["id"]
        latest = latest_by_patient.get(pid)
        enriched = {
            **patient,
            "assessment_count": count_by_patient.get(pid, 0),
            "latest_assessment_row": latest,
        }
        if query and query.lower() not in enriched["name"].lower() and query.lower() not in pid.lower():
            continue
        if language and enriched.get("preferred_language") != language:
            continue
        if needs_review is not None:
            latest_needs_review = bool(latest["needs_clinician_review"]) if latest else False
            if latest_needs_review != needs_review:
                continue
        results.append(enriched)

    return results


# --- Clinicians -----------------------------------------------------------


def get_clinician_by_email(email: str, db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM clinicians WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row is not None else None


def create_clinician_row(
    clinician_id: str,
    name: str,
    email: str,
    password_hash: str,
    role: str = "Clinical Professional",
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO clinicians "
            "(id, name, email, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (clinician_id, name, email, password_hash, role, datetime.now(UTC).isoformat()),
        )


# --- Sessions -----------------------------------------------------------


def create_session(
    token: str,
    subject_type: str,
    subject_id: str,
    expires_at: str,
    db_path: Path | None = None,
) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sessions (token, subject_type, subject_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token, subject_type, subject_id, datetime.now(UTC).isoformat(), expires_at),
        )


def get_session(token: str, db_path: Path | None = None) -> dict | None:
    """Returns the session row if token exists and hasn't expired (expired
    rows are lazily deleted here rather than needing a background sweep)."""
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        if row["expires_at"] < datetime.now(UTC).isoformat():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        return dict(row)


def delete_session(token: str, db_path: Path | None = None) -> None:
    with sqlite3.connect(db_path or DB_PATH) as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
