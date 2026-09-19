"""DEMO-ONLY stubs for the frontend's participant-login screen.

Not real authentication or patient management -- just enough for
PatientLogin.jsx to get past the RequireParticipant guard so the rest of
the flow (Language -> Task -> Recording -> Processing -> Complete) can be
exercised against the real backend. Delete this file once real participant
management/auth is built (see docs/ACTION_PLAN.md Track C).
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_DEMO_PATIENT = {"patientId": "demo-patient", "name": "Demo Patient"}


class ParticipantCodeRequest(BaseModel):
    code: str


@router.post("/auth/participant")
def verify_participant_code(payload: ParticipantCodeRequest) -> dict:
    # Accepts any non-empty code, no real lookup/auth.
    return _DEMO_PATIENT


@router.get("/patients")
def list_patients() -> list[dict]:
    return [{"id": _DEMO_PATIENT["patientId"], "name": _DEMO_PATIENT["name"]}]
