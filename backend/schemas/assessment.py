from pydantic import BaseModel, ConfigDict, Field


class AssessmentResult(BaseModel):
    assessment_id: str
    language: str
    risk_score: float
    speech_features: dict
    linguistic_features: dict
    model_version: str
    needs_clinician_review: bool


class AssessmentCreate(BaseModel):
    """Request body for POST /assessments. The frontend sends camelCase
    keys (frontend/src/pages/patient/Task.jsx) -- the alias is load-bearing,
    not stylistic."""

    model_config = ConfigDict(populate_by_name=True)

    patient_id: str = Field(alias="patientId")
    language: str
    task_id: str = Field(alias="taskId")


class AssessmentCreateResponse(BaseModel):
    id: str
    status: str


class AssessmentAudioResponse(BaseModel):
    id: str
    status: str
