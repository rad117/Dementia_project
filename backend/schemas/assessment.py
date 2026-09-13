from pydantic import BaseModel


class AssessmentResult(BaseModel):
    assessment_id: str
    language: str
    risk_score: float
    speech_features: dict
    linguistic_features: dict
    model_version: str
    needs_clinician_review: bool
