import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend import db
from backend.schemas.assessment import (
    AssessmentAudioResponse,
    AssessmentCreate,
    AssessmentCreateResponse,
)
from backend.schemas.results import AssessmentInfo, AssessmentResultsV2
from backend.services.results_mapper import build_assessment_info, build_results, find_previous_assessment_row
from ml.inference.predict import AudioProcessingError, predict

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/assessments", response_model=AssessmentCreateResponse, status_code=201)
def create_assessment(payload: AssessmentCreate) -> AssessmentCreateResponse:
    assessment_id = str(uuid.uuid4())
    db.create_assessment_row(assessment_id, payload.patient_id, payload.language, payload.task_id)
    return AssessmentCreateResponse(id=assessment_id, status="pending_recording")


@router.post("/assessments/{assessment_id}/audio", response_model=AssessmentAudioResponse)
async def upload_assessment_audio(
    assessment_id: str, audio: UploadFile = File(...)
) -> AssessmentAudioResponse:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    audio_bytes = await audio.read()
    try:
        result = predict(audio_bytes, task_id=row["task_id"], language=row["language"])
    except AudioProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.save_result_row(assessment_id, **result)
    return AssessmentAudioResponse(id=assessment_id, status="complete")


@router.get("/assessments/{assessment_id}", response_model=AssessmentInfo)
def get_assessment(assessment_id: str) -> AssessmentInfo:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return AssessmentInfo(**build_assessment_info(row))


@router.get("/assessments/{assessment_id}/results", response_model=AssessmentResultsV2)
def get_assessment_results(assessment_id: str) -> AssessmentResultsV2:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if row["status"] != "complete":
        raise HTTPException(status_code=409, detail="Assessment not yet processed")

    previous_row = find_previous_assessment_row(row["patient_id"], assessment_id)
    return AssessmentResultsV2(**build_results(row, previous_row))
