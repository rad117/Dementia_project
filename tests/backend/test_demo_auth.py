import pytest
from fastapi.testclient import TestClient

import backend.db as db_module
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    # Route handlers call db.* without an explicit db_path, so they always
    # hit the module-level default -- point that at a throwaway file per
    # test instead of the real dev DB.
    test_db_path = tmp_path / "test_assessments.db"
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    db_module.init_db(test_db_path)


def test_verify_participant_code_accepts_any_non_empty_code():
    response = client.post("/auth/participant", json={"code": "anything"})

    assert response.status_code == 200
    body = response.json()
    assert body["patientId"] == "demo-patient"
    assert body["name"] == "Demo Patient"


def test_verify_participant_code_returns_same_patient_regardless_of_code():
    first = client.post("/auth/participant", json={"code": "abc123"}).json()
    second = client.post("/auth/participant", json={"code": "xyz789"}).json()

    assert first == second


def test_list_patients_returns_demo_patient():
    response = client.get("/patients")

    assert response.status_code == 200
    body = response.json()
    assert body == [{"id": "demo-patient", "name": "Demo Patient"}]


def test_get_patient_returns_demo_patient():
    response = client.get("/patients/demo-patient")

    assert response.status_code == 200
    assert response.json() == {"id": "demo-patient", "name": "Demo Patient"}


def test_get_patient_404_for_unknown_id():
    response = client.get("/patients/unknown-id")

    assert response.status_code == 404


def test_list_patient_assessments_returns_only_complete_ones_newest_first():
    db_module.create_assessment_row("a-pending", "demo-patient", "en", "cookie-theft")
    db_module.create_assessment_row("a-older", "demo-patient", "en", "cookie-theft")
    db_module.save_result_row(
        "a-older",
        risk_score=0.2,
        speech_features={},
        linguistic_features={},
        semantic_features={},
        production_features={},
        quality_signals={},
        transcript=None,
        raw_features={},
        model_version="stub-v0",
        needs_clinician_review=False,
    )
    db_module.create_assessment_row("a-newer", "demo-patient", "en", "cookie-theft")
    db_module.save_result_row(
        "a-newer",
        risk_score=0.6,
        speech_features={},
        linguistic_features={},
        semantic_features={},
        production_features={},
        quality_signals={},
        transcript=None,
        raw_features={},
        model_version="stub-v0",
        needs_clinician_review=True,
    )

    response = client.get("/patients/demo-patient/assessments")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == ["a-newer", "a-older"]
    assert body[0]["needsClinicianReview"] is True
    assert body[0]["riskScore"] == 0.6


def test_list_patient_assessments_404_for_unknown_patient():
    response = client.get("/patients/unknown-id/assessments")

    assert response.status_code == 404


def test_login_clinical_user_accepts_any_credentials():
    response = client.post(
        "/auth/clinical", json={"email": "dr.sharma@memora.org", "password": "demo1234"}
    )

    assert response.status_code == 200
    assert response.json() == {"name": "Dr. Sharma", "role": "Clinical Professional"}


def test_login_clinical_user_requires_email_and_password():
    response = client.post("/auth/clinical", json={"email": "dr.sharma@memora.org"})

    assert response.status_code == 422
