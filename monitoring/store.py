"""SQLite persistence for safety-monitoring alerts and observations.

Same conventions as backend/db.py: stdlib sqlite3, one connection per call,
and the same database file, so assessments and monitoring events live side
by side and can be joined on patient_id.

The database path is looked up at call time (not import time) so tests can
point backend.db.DB_PATH at a temporary file.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from backend import db as backend_db

# Raw observations describe a real person in a real room. Keep only the most
# recent ones; alerts are the durable care record.
MAX_OBSERVATIONS = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence TEXT NOT NULL,
    action TEXT NOT NULL,
    patient_id TEXT,
    source TEXT NOT NULL DEFAULT 'live'
);
CREATE TABLE IF NOT EXISTS monitoring_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    patient_id TEXT,
    source TEXT NOT NULL DEFAULT 'live',
    data TEXT NOT NULL
);
"""


def _path(db_path: Path | None) -> Path:
    return db_path or backend_db.DB_PATH


def init_db(db_path: Path | None = None) -> None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.executescript(_SCHEMA)


def save_alerts(
    events: list[dict],
    *,
    patient_id: str | None = None,
    source: str = "live",
    db_path: Path | None = None,
) -> None:
    if not events:
        return
    with sqlite3.connect(_path(db_path)) as conn:
        conn.executemany(
            "INSERT INTO monitoring_alerts "
            "(at, level, kind, summary, evidence, action, patient_id, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (e["at"], e["level"], e["kind"], e["summary"], e["evidence"],
                 e["action"], patient_id, source)
                for e in events
            ],
        )


def save_observation(
    obs: dict,
    *,
    at: datetime,
    patient_id: str | None = None,
    source: str = "live",
    db_path: Path | None = None,
) -> None:
    clean = {k: v for k, v in obs.items() if not k.startswith("_")}
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute(
            "INSERT INTO monitoring_observations (at, patient_id, source, data) "
            "VALUES (?, ?, ?, ?)",
            (at.isoformat(timespec="seconds"), patient_id, source,
             json.dumps(clean, ensure_ascii=False)),
        )
        conn.execute(
            "DELETE FROM monitoring_observations WHERE id NOT IN "
            "(SELECT id FROM monitoring_observations ORDER BY id DESC LIMIT ?)",
            (MAX_OBSERVATIONS,),
        )


def list_alerts(
    *,
    limit: int = 50,
    patient_id: str | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    query = "SELECT * FROM monitoring_alerts"
    params: list = []
    if patient_id:
        query += " WHERE patient_id = ?"
        params.append(patient_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def last_observation(db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT at, patient_id, source, data FROM monitoring_observations "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "at": row["at"],
        "patient_id": row["patient_id"],
        "source": row["source"],
        "observation": json.loads(row["data"]),
    }


def clear_source(source: str, db_path: Path | None = None) -> int:
    """Delete all alerts/observations from one source (used to reset demo data)."""
    with sqlite3.connect(_path(db_path)) as conn:
        a = conn.execute("DELETE FROM monitoring_alerts WHERE source = ?", (source,)).rowcount
        conn.execute("DELETE FROM monitoring_observations WHERE source = ?", (source,))
    return a
