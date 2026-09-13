from backend.services.mock_inference import generate_mock_result


def test_generate_mock_result_shape():
    result = generate_mock_result(b"", "en", "cookie-theft")

    assert result.language == "en"
    assert result.model_version == "mock-0.0"
    assert isinstance(result.risk_score, float)
    assert isinstance(result.needs_clinician_review, bool)


def test_generate_mock_result_unique_ids():
    first = generate_mock_result(b"", "en", "cookie-theft")
    second = generate_mock_result(b"", "en", "cookie-theft")

    assert first.assessment_id != second.assessment_id
