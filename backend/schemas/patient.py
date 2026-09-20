from pydantic import BaseModel, ConfigDict, Field


class PatientResponse(BaseModel):
    id: str
    name: str


class AssessmentSummary(BaseModel):
    """Response shape for GET /patients/{id}/assessments -- camelCase aliases
    to match the frontend's convention (see AssessmentCreate)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    patient_id: str = Field(alias="patientId")
    language: str
    task_id: str = Field(alias="taskId")
    status: str
    risk_score: float = Field(alias="riskScore")
    needs_clinician_review: bool = Field(alias="needsClinicianReview")
    created_at: str = Field(alias="createdAt")
    completed_at: str = Field(alias="completedAt")
