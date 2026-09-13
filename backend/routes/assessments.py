from fastapi import APIRouter, File, Form, UploadFile

from backend.schemas.assessment import AssessmentResult
from backend.services.mock_inference import generate_mock_result

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/assessments", response_model=AssessmentResult)
async def create_assessment(
    audio: UploadFile = File(...),
    language: str = Form(...),
    task_id: str = Form(...),
) -> AssessmentResult:
    await audio.read()  # Phase 0: audio is discarded, not processed or stored.
    return generate_mock_result(language, task_id)
