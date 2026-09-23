import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from backend import db
from backend.schemas.assessment import (
    AssessmentAudioResponse,
    AssessmentCreate,
    AssessmentCreateResponse,
)
from backend.schemas.results import AssessmentInfo, AssessmentResultsV2
from backend.services.auth import require_clinician, require_participant, require_subject
from backend.services.results_mapper import build_assessment_info, build_results, find_previous_assessment_row
from ml.inference.predict import AudioProcessingError, predict

router = APIRouter()


def _check_owns_row(subject: dict, patient_id: str) -> None:
    if subject["type"] == "participant" and subject["id"] != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this assessment")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/assessments", response_model=list[AssessmentInfo])
def list_assessments(
    needs_review: bool | None = Query(None, alias="needsReview"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _subject: dict = Depends(require_clinician),
) -> list[AssessmentInfo]:
    rows = db.list_all_assessments(needs_review=needs_review, limit=limit, offset=offset)
    return [AssessmentInfo(**build_assessment_info(row)) for row in rows]


@router.post("/assessments", response_model=AssessmentCreateResponse, status_code=201)
def create_assessment(
    payload: AssessmentCreate, subject: dict = Depends(require_participant)
) -> AssessmentCreateResponse:
    if subject["id"] != payload.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to create an assessment for this patient")
    assessment_id = str(uuid.uuid4())
    try:
        db.create_assessment_row(assessment_id, payload.patient_id, payload.language, payload.task_id)
    except db.PatientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Patient not found") from exc
    return AssessmentCreateResponse(id=assessment_id, status="pending_recording")


@router.post("/assessments/{assessment_id}/audio", response_model=AssessmentAudioResponse)
async def upload_assessment_audio(
    assessment_id: str,
    audio: UploadFile = File(...),
    subject: dict = Depends(require_subject),
) -> AssessmentAudioResponse:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    _check_owns_row(subject, row["patient_id"])

    audio_bytes = await audio.read()
    try:
        result = predict(audio_bytes, task_id=row["task_id"], language=row["language"])
    except AudioProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.save_result_row(assessment_id, **result)
    return AssessmentAudioResponse(id=assessment_id, status="complete")


@router.get("/assessments/{assessment_id}", response_model=AssessmentInfo)
def get_assessment(assessment_id: str, subject: dict = Depends(require_subject)) -> AssessmentInfo:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    _check_owns_row(subject, row["patient_id"])
    return AssessmentInfo(**build_assessment_info(row))


@router.get("/assessments/{assessment_id}/results", response_model=AssessmentResultsV2)
def get_assessment_results(assessment_id: str, subject: dict = Depends(require_subject)) -> AssessmentResultsV2:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    _check_owns_row(subject, row["patient_id"])
    if row["status"] != "complete":
        raise HTTPException(status_code=409, detail="Assessment not yet processed")

    previous_row = find_previous_assessment_row(row["patient_id"], assessment_id)
    return AssessmentResultsV2(**build_results(row, previous_row))
