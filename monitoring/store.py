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
    source TEXT NOT NULL DEFAULT 'live',
    scenario TEXT
);
CREATE TABLE IF NOT EXISTS guardian_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'sms',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    patient_id TEXT,
    contact_id INTEGER,
    channel TEXT NOT NULL,
    alert_kind TEXT,
    status TEXT NOT NULL,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created REAL NOT NULL,
    next_try REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    patient_id TEXT,
    contact_id INTEGER NOT NULL,
    alert_kind TEXT,
    body TEXT NOT NULL
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
        # Databases created before demo scenarios existed lack this column.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(monitoring_alerts)")}
        if "scenario" not in cols:
            conn.execute("ALTER TABLE monitoring_alerts ADD COLUMN scenario TEXT")


def save_alerts(
    events: list[dict],
    *,
    patient_id: str | None = None,
    source: str = "live",
    scenario: str | None = None,
    db_path: Path | None = None,
) -> None:
    if not events:
        return
    with sqlite3.connect(_path(db_path)) as conn:
        conn.executemany(
            "INSERT INTO monitoring_alerts "
            "(at, level, kind, summary, evidence, action, patient_id, source, scenario) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (e["at"], e["level"], e["kind"], e["summary"], e["evidence"],
                 e["action"], patient_id, source, scenario)
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


def last_observation(patient_id: str | None = None, db_path: Path | None = None) -> dict | None:
    """The newest observation, or the newest for one patient when one is given."""
    query = "SELECT at, patient_id, source, data FROM monitoring_observations"
    params: list = []
    if patient_id:
        query += " WHERE patient_id = ?"
        params.append(patient_id)
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(query + " ORDER BY id DESC LIMIT 1", params).fetchone()
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


def clear_demo_scenario(scenario: str, patient_id: str | None, db_path: Path | None = None) -> int:
    """Delete earlier demo alerts of one scenario for one patient (or for no patient)."""
    with sqlite3.connect(_path(db_path)) as conn:
        return conn.execute(
            "DELETE FROM monitoring_alerts WHERE source = 'demo' AND scenario = ? "
            "AND patient_id IS ?",
            (scenario, patient_id),
        ).rowcount


# ---------------------------------------------------------------------------
# guardian contacts + notification log (Twilio SMS / WhatsApp alerts)

def add_contact(patient_id: str, name: str, phone: str, channel: str = "sms",
                db_path: Path | None = None) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(_path(db_path)) as conn:
        cur = conn.execute(
            "INSERT INTO guardian_contacts (patient_id, name, phone, channel, created_at) "
            "VALUES (?, ?, ?, ?, ?)", (patient_id, name, phone, channel, now))
        return {"id": cur.lastrowid, "patient_id": patient_id, "name": name,
                "phone": phone, "channel": channel, "created_at": now}


def list_contacts(patient_id: str | None = None, db_path: Path | None = None) -> list[dict]:
    query, params = "SELECT * FROM guardian_contacts", []
    if patient_id:
        query += " WHERE patient_id = ?"
        params.append(patient_id)
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query + " ORDER BY id", params).fetchall()]


def get_contact(contact_id: int, db_path: Path | None = None) -> dict | None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM guardian_contacts WHERE id = ?", (contact_id,)).fetchone()
        return dict(row) if row else None


def delete_contact(contact_id: int, db_path: Path | None = None) -> bool:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute("DELETE FROM notification_queue WHERE contact_id = ?", (contact_id,))
        return conn.execute("DELETE FROM guardian_contacts WHERE id = ?", (contact_id,)).rowcount > 0


def log_notification(*, patient_id: str | None, contact_id: int | None, channel: str,
                     alert_kind: str | None, status: str, detail: str | None = None,
                     db_path: Path | None = None) -> None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute(
            "INSERT INTO notification_log (at, patient_id, contact_id, channel, alert_kind, status, detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), patient_id, contact_id, channel,
             alert_kind, status, (detail or "")[:300]))


def list_notifications(limit: int = 50, db_path: Path | None = None) -> list[dict]:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(
            "SELECT * FROM notification_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


# ---------------------------------------------------------------------------
# notification queue: messages not yet delivered, so a restart cannot lose them.
# Times are Unix seconds, since they have to mean the same thing after a restart.

def enqueue_notification(*, patient_id: str | None, contact_id: int, alert_kind: str | None,
                         body: str, created: float, db_path: Path | None = None) -> None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute(
            "INSERT INTO notification_queue (created, next_try, patient_id, contact_id, alert_kind, body) "
            "VALUES (?, ?, ?, ?, ?, ?)", (created, created, patient_id, contact_id, alert_kind, body))


def is_notification_queued(contact_id: int, alert_kind: str | None, db_path: Path | None = None) -> bool:
    with sqlite3.connect(_path(db_path)) as conn:
        return conn.execute(
            "SELECT 1 FROM notification_queue WHERE contact_id = ? AND alert_kind IS ? LIMIT 1",
            (contact_id, alert_kind)).fetchone() is not None


def due_notifications(now: float, db_path: Path | None = None) -> list[dict]:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(
            "SELECT * FROM notification_queue WHERE next_try <= ? ORDER BY id", (now,)).fetchall()]


def next_queued_time(db_path: Path | None = None) -> float | None:
    with sqlite3.connect(_path(db_path)) as conn:
        return conn.execute("SELECT MIN(next_try) FROM notification_queue").fetchone()[0]


def reschedule_notification(queue_id: int, *, attempts: int, next_try: float,
                            db_path: Path | None = None) -> None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute("UPDATE notification_queue SET attempts = ?, next_try = ? WHERE id = ?",
                     (attempts, next_try, queue_id))


def remove_queued_notification(queue_id: int, db_path: Path | None = None) -> None:
    with sqlite3.connect(_path(db_path)) as conn:
        conn.execute("DELETE FROM notification_queue WHERE id = ?", (queue_id,))
