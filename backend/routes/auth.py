"""Real authentication and patient management -- replaces the old
backend/routes/demo_auth.py stub (any credentials logged in, every patient
endpoint hardcoded to one record). See backend/services/auth.py for the
hashing/token mechanism this builds on.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from backend import db
from backend.schemas.auth import (
    AssistedLoginRequest,
    ClinicalLoginRequest,
    ClinicalLoginResponse,
    ParticipantCodeRequest,
    ParticipantLoginResponse,
)
from backend.schemas.patient import AssessmentSummary, PatientListItem, PatientResponse
from backend.services.auth import (
    extract_token,
    get_optional_subject,
    issue_token,
    require_subject,
    verify_password,
)
from backend.services.results_mapper import build_assessment_info

router = APIRouter()


@router.post("/auth/participant", response_model=ParticipantLoginResponse)
def verify_participant_code(payload: ParticipantCodeRequest) -> ParticipantLoginResponse:
    patient = db.get_patient_by_login_code(payload.code.strip())
    if patient is None:
        raise HTTPException(status_code=401, detail="That participant code was not found.")
    token = issue_token("participant", patient["id"])
    return ParticipantLoginResponse(patient_id=patient["id"], name=patient["name"], token=token)


@router.post("/auth/participant/assisted", response_model=ParticipantLoginResponse)
def assisted_participant_login(payload: AssistedLoginRequest) -> ParticipantLoginResponse:
    """Staff-assisted start from PatientLogin.jsx's unauthenticated
    "Assisted start" picker. Intentionally unauthenticated itself -- it only
    grants a session for a patient_id already visible via the public GET
    /patients roster, no more trust than the previous client-side-only
    behavior it replaces, but it now issues a real token so the rest of the
    flow (POST /assessments, etc.) doesn't 401."""
    patient = db.get_patient_row(payload.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    token = issue_token("participant", patient["id"])
    return ParticipantLoginResponse(patient_id=patient["id"], name=patient["name"], token=token)


@router.post("/auth/clinical", response_model=ClinicalLoginResponse)
def login_clinical_user(payload: ClinicalLoginRequest) -> ClinicalLoginResponse:
    clinician = db.get_clinician_by_email(payload.email.strip().lower())
    if clinician is None or not verify_password(payload.password, clinician["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = issue_token("clinician", clinician["id"])
    return ClinicalLoginResponse(name=clinician["name"], role=clinician["role"], token=token)


@router.post("/auth/logout", status_code=204)
def logout(
    _subject: dict = Depends(require_subject),
    authorization: str | None = Header(default=None),
) -> None:
    token = extract_token(authorization)
    if token:
        db.delete_session(token)


@router.get("/patients")
def list_patients(
    q: str | None = Query(None, alias="query"),
    language: str | None = Query(None),
    review_status: str | None = Query(None, alias="reviewStatus"),
    sort: str = Query("recent"),
    subject: dict | None = Depends(get_optional_subject),
) -> list[PatientResponse] | list[PatientListItem]:
    if subject is None or subject["type"] != "clinician":
        # Minimal shape for the unauthenticated "assisted start" picker.
        rows = db.list_patients()
        return [PatientResponse(id=row["id"], name=row["name"]) for row in rows]

    needs_review = None
    if review_status == "needs-review":
        needs_review = True
    elif review_status == "reviewed":
        needs_review = False

    # Patients.jsx's language <select> sends the literal string "all" for
    # its default option, not an omitted param -- treat it the same as
    # "no filter" (matching how review_status's "all" is already handled
    # above by simply not matching either real value).
    language_filter = language if language and language != "all" else None

    rows = db.list_patients(query=q, language=language_filter, needs_review=needs_review)

    items = [
        PatientListItem(
            id=row["id"],
            name=row["name"],
            preferred_language=row["preferred_language"],
            age=row["age"],
            assessment_count=row["assessment_count"],
            latest_assessment=(
                build_assessment_info(row["latest_assessment_row"])
                if row["latest_assessment_row"]
                else None
            ),
        )
        for row in rows
    ]

    if sort == "name":
        items.sort(key=lambda p: p.name)
    elif sort == "review":
        items.sort(key=lambda p: bool(p.latest_assessment and p.latest_assessment.screening and p.latest_assessment.screening.needs_clinician_review), reverse=True)
    else:
        items.sort(key=lambda p: p.latest_assessment.date if p.latest_assessment else "", reverse=True)

    return items


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, subject: dict = Depends(require_subject)) -> PatientResponse:
    if subject["type"] == "participant" and subject["id"] != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this patient")
    patient = db.get_patient_row(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse(
        id=patient["id"],
        name=patient["name"],
        preferred_language=patient["preferred_language"],
        age=patient["age"],
    )


@router.get("/patients/{patient_id}/assessments", response_model=list[AssessmentSummary])
def list_patient_assessments(
    patient_id: str, subject: dict = Depends(require_subject)
) -> list[AssessmentSummary]:
    if subject["type"] == "participant" and subject["id"] != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this patient")
    if db.get_patient_row(patient_id) is None:
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
