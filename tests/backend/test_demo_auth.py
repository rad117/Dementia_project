from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


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
