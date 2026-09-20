"""DEMO-ONLY stubs for the frontend's participant-login screen.

Not real authentication or patient management -- just enough for
PatientLogin.jsx to get past the RequireParticipant guard so the rest of
the flow (Language -> Task -> Recording -> Processing -> Complete) can be
exercised against the real backend. Delete this file once real participant
management/auth is built (see docs/ACTION_PLAN.md Track C).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import db
from backend.schemas.patient import AssessmentSummary, PatientResponse

router = APIRouter()

_DEMO_PATIENT = {"patientId": "demo-patient", "name": "Demo Patient"}
_DEMO_CLINICIAN = {"name": "Dr. Sharma", "role": "Clinical Professional"}


class ParticipantCodeRequest(BaseModel):
    code: str


class ClinicalLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/participant")
def verify_participant_code(payload: ParticipantCodeRequest) -> dict:
    # Accepts any non-empty code, no real lookup/auth.
    return _DEMO_PATIENT


@router.post("/auth/clinical")
def login_clinical_user(payload: ClinicalLoginRequest) -> dict:
    # Accepts any email/password, no real lookup/auth.
    return _DEMO_CLINICIAN


@router.get("/patients")
def list_patients() -> list[dict]:
    return [{"id": _DEMO_PATIENT["patientId"], "name": _DEMO_PATIENT["name"]}]


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str) -> PatientResponse:
    if patient_id != _DEMO_PATIENT["patientId"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse(id=_DEMO_PATIENT["patientId"], name=_DEMO_PATIENT["name"])


@router.get("/patients/{patient_id}/assessments", response_model=list[AssessmentSummary])
def list_patient_assessments(patient_id: str) -> list[AssessmentSummary]:
    if patient_id != _DEMO_PATIENT["patientId"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    rows = db.list_assessments_by_patient(patient_id)
    return [
        AssessmentSummary(
            id=row["id"],
            patient_id=row["patient_id"],
            language=row["language"],
            task_id=row["task_id"],
            status=row["status"],
            risk_score=row["risk_score"],
            needs_clinician_review=bool(row["needs_clinician_review"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
        for row in rows
    ]
