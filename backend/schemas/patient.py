from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.results import AssessmentInfo, _CamelModel


class PatientResponse(_CamelModel):
    """Minimal shape -- used for the unauthenticated participant-facing
    roster (PatientLogin.jsx's "Assisted start" picker) and GET
    /patients/{id}. Optional fields default to None rather than being
    required, since the "assisted start" caller never needs them."""

    id: str
    name: str
    preferred_language: str | None = None
    age: int | None = None


class PatientListItem(_CamelModel):
    """Full shape -- the authenticated clinician-facing GET /patients
    response (Patients.jsx's roster table)."""

    id: str
    name: str
    preferred_language: str | None = None
    age: int | None = None
    assessment_count: int
    latest_assessment: AssessmentInfo | None = None


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
