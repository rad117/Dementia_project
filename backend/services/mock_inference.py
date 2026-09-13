import uuid

from backend.schemas.assessment import AssessmentResult


def generate_mock_result(language: str, task_id: str) -> AssessmentResult:
    return AssessmentResult(
        assessment_id=str(uuid.uuid4()),
        language=language,
        risk_score=0.42,
        speech_features={
            "duration_seconds": 45.2,
            "pause_count": 6,
            "speech_rate_wpm": 118.0,
        },
        linguistic_features={
            "lexical_diversity": 0.61,
            "word_count": 87,
            "filler_word_count": 4,
        },
        model_version="mock-0.0",
        needs_clinician_review=True,
    )
