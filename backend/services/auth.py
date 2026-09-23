"""Password hashing, session tokens, and FastAPI auth dependencies.

Deliberately minimal for this project's scale (a demo/research tool, not a
production HIPAA system): stdlib PBKDF2-HMAC-SHA256 for password hashing
(no bcrypt/passlib dependency), opaque bearer tokens stored in the
`sessions` table (no JWT -- nothing needs client-decodable claims, and an
opaque token is trivially revocable via DELETE). Tokens are meant to live
only in memory on the frontend (see frontend/src/app/SessionContext.jsx's
"nothing persists across a hard refresh" privacy requirement) -- the
12-hour server-side TTL here is a backstop, not the primary session
boundary.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException

from backend import db

_SESSION_TTL = timedelta(hours=12)
_PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return secrets.compare_digest(expected.hex(), digest_hex)


def issue_token(subject_type: str, subject_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(UTC) + _SESSION_TTL).isoformat()
    db.create_session(token, subject_type, subject_id, expires_at)
    return token


def extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip() or None


def get_optional_subject(authorization: str | None = Header(default=None)) -> dict | None:
    """Returns {"type": "participant"|"clinician", "id": subject_id} for a
    valid bearer token, or None if absent/invalid -- never raises. Used by
    routes (like GET /patients) whose response shape varies by caller
    rather than requiring auth outright."""
    token = extract_token(authorization)
    if token is None:
        return None
    session = db.get_session(token)
    if session is None:
        return None
    return {"type": session["subject_type"], "id": session["subject_id"]}


def require_subject(authorization: str | None = Header(default=None)) -> dict:
    """Any valid token, participant or clinician. 401 if missing/invalid/expired."""
    subject = get_optional_subject(authorization)
    if subject is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return subject


def require_clinician(authorization: str | None = Header(default=None)) -> dict:
    subject = require_subject(authorization)
    if subject["type"] != "clinician":
        raise HTTPException(status_code=403, detail="Clinician access required")
    return subject


def require_participant(authorization: str | None = Header(default=None)) -> dict:
    subject = require_subject(authorization)
    if subject["type"] != "participant":
        raise HTTPException(status_code=403, detail="Participant access required")
    return subject
