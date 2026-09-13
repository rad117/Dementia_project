from backend.schemas.assessment import AssessmentResult


def test_assessment_result_round_trip():
    result = AssessmentResult(
        assessment_id="abc-123",
        language="en",
        risk_score=0.42,
        speech_features={"pause_count": 3},
        linguistic_features={"lexical_diversity": 0.5},
        model_version="mock-0.0",
        needs_clinician_review=True,
    )

    dumped = result.model_dump()

    assert dumped["assessment_id"] == "abc-123"
    assert dumped["model_version"] == "mock-0.0"
    assert dumped["needs_clinician_review"] is True
