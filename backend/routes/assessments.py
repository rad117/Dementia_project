import json
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend import db
from backend.schemas.assessment import (
    AssessmentAudioResponse,
    AssessmentCreate,
    AssessmentCreateResponse,
    AssessmentResult,
)
from backend.services.mock_inference import generate_mock_result
from ml.inference.predict import AudioProcessingError, predict

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/assessments", response_model=AssessmentResult)
async def create_assessment_legacy_mock(
    audio: UploadFile = File(...),
    language: str = Form(...),
    task_id: str = Form(...),
) -> AssessmentResult:
    # Legacy/demo-only endpoint, superseded by the 3-step contract below
    # (POST /assessments -> POST /assessments/{id}/audio -> GET
    # /assessments/{id}/results). Kept as a zero-dependency mock-vs-real
    # comparison harness and curl smoke test (see backend/README.md).
    audio_bytes = await audio.read()
    return generate_mock_result(audio_bytes, language, task_id)


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


@router.get("/assessments/{assessment_id}/results", response_model=AssessmentResult)
def get_assessment_results(assessment_id: str) -> AssessmentResult:
    row = db.get_assessment_row(assessment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if row["status"] != "complete":
        raise HTTPException(status_code=409, detail="Assessment not yet processed")

    return AssessmentResult(
        assessment_id=row["id"],
        language=row["language"],
        risk_score=row["risk_score"],
        speech_features=json.loads(row["speech_features"]),
        linguistic_features=json.loads(row["linguistic_features"]),
        model_version=row["model_version"],
        needs_clinician_review=bool(row["needs_clinician_review"]),
    )
