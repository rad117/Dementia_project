"""Idempotent demo-data seeding, run from main.py's lifespan on every
startup (same pattern as db.init_db()).

Seeds three things, all via INSERT OR IGNORE so re-running is a no-op once
seeded:

1. A `patients` row for id="demo-patient" -- the live backend/assessments.db
   has pre-existing assessment rows from before real patients existed, all
   pointing at patient_id="demo-patient". Once create_assessment_row()
   enforces patient existence, those rows must keep resolving.
2. The same CA-100x/PT-100x patient roster as
   frontend/src/data/mockPatients.js, so the mock-API demo and the real
   backend show the same patients -- picking a login code (e.g. "PT-1001")
   in the frontend's mock-mode "Enter your participant code" screen works
   identically in real mode.
3. A demo clinician (dr.sharma@memora.org / demo1234) matching
   ClinicalLogin.jsx's "Fill Demo Clinician" quick-access button, so that
   button keeps working unchanged against the real backend.
"""

from backend import db
from backend.services.auth import hash_password

_MOCK_PATIENTS = [
    {"id": "CA-1001", "name": "Rajesh Kumar", "age": 71, "preferred_language": "Hindi", "login_code": "PT-1001"},
    {"id": "CA-1002", "name": "Anita Shah", "age": 68, "preferred_language": "Marathi", "login_code": "PT-1002"},
    {"id": "CA-1003", "name": "Meena Iyer", "age": 74, "preferred_language": "Tamil", "login_code": "PT-1003"},
    {"id": "CA-1004", "name": "Abdul Rahman", "age": 69, "preferred_language": "Urdu", "login_code": "PT-1004"},
    {"id": "CA-1005", "name": "Sunita Das", "age": 77, "preferred_language": "Bengali", "login_code": "PT-1005"},
    {"id": "CA-1006", "name": "Joseph Thomas", "age": 66, "preferred_language": "English", "login_code": "PT-1006"},
    {"id": "CA-1007", "name": "Lakshmi Venkataraman Subramaniam", "age": 72, "preferred_language": "Telugu", "login_code": "PT-1007"},
    {"id": "CA-1008", "name": "Ravi Shankar Nair", "age": 70, "preferred_language": "Kannada", "login_code": "PT-1008"},
    {"id": "CA-1009", "name": "Fatima Sheikh", "age": 65, "preferred_language": "Urdu", "login_code": "PT-1009"},
    {"id": "CA-1010", "name": "David Fernandes", "age": 73, "preferred_language": "English", "login_code": "PT-1010"},
]


def run(db_path=None) -> None:
    db.create_patient_row(
        "demo-patient", "Demo Patient", login_code="PT-0000", db_path=db_path
    )
    for patient in _MOCK_PATIENTS:
        db.create_patient_row(
            patient["id"],
            patient["name"],
            login_code=patient["login_code"],
            preferred_language=patient["preferred_language"],
            age=patient["age"],
            db_path=db_path,
        )

    db.create_clinician_row(
        "dr-sharma",
        "Dr. Sharma",
        email="dr.sharma@memora.org",
        password_hash=hash_password("demo1234"),
        db_path=db_path,
    )
