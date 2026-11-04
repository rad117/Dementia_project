from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth import hash_password, issue_token, verify_password

client = TestClient(app)


# --- password hashing -----------------------------------------------------


def test_hash_password_round_trips():
    hashed = hash_password("demo1234")
    assert verify_password("demo1234", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("demo1234")
    assert not verify_password("wrong", hashed)


def test_hash_password_uses_a_random_salt_each_time():
    assert hash_password("demo1234") != hash_password("demo1234")


# --- participant login (by code) ------------------------------------------


def test_participant_login_with_seeded_code_succeeds():
    response = client.post("/auth/participant", json={"code": "PT-1001"})

    assert response.status_code == 200
    body = response.json()
    assert body["patientId"] == "CA-1001"
    assert body["name"] == "Rajesh Kumar"
    assert body["token"]


def test_participant_login_with_unknown_code_returns_401():
    response = client.post("/auth/participant", json={"code": "not-a-real-code"})

    assert response.status_code == 401


def test_participant_token_grants_access_to_own_patient_record():
    token = client.post("/auth/participant", json={"code": "PT-1001"}).json()["token"]

    response = client.get("/patients/CA-1001", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["id"] == "CA-1001"


def test_participant_token_403_for_a_different_patient_record():
    token = client.post("/auth/participant", json={"code": "PT-1001"}).json()["token"]

    response = client.get("/patients/CA-1002", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


# --- assisted participant login --------------------------------------------


def test_assisted_login_issues_a_working_token():
    response = client.post("/auth/participant/assisted", json={"patientId": "CA-1002"})

    assert response.status_code == 200
    body = response.json()
    assert body["patientId"] == "CA-1002"
    assert body["name"] == "Anita Shah"

    # The whole point: this token actually authenticates on the next call.
    follow_up = client.get("/patients/CA-1002", headers={"Authorization": f"Bearer {body['token']}"})
    assert follow_up.status_code == 200


def test_assisted_login_404_for_unknown_patient():
    response = client.post("/auth/participant/assisted", json={"patientId": "not-a-real-id"})

    assert response.status_code == 404


# --- clinical login ---------------------------------------------------------


def test_clinical_login_with_seeded_credentials_succeeds():
    response = client.post(
        "/auth/clinical", json={"email": "dr.sharma@memora.org", "password": "demo1234"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"name": "Dr. Sharma", "role": "Clinical Professional", "token": body["token"]}
    assert body["token"]


def test_clinical_login_with_wrong_password_returns_401():
    response = client.post(
        "/auth/clinical", json={"email": "dr.sharma@memora.org", "password": "wrong"}
    )

    assert response.status_code == 401


def test_clinical_login_with_unknown_email_returns_401():
    response = client.post(
        "/auth/clinical", json={"email": "nobody@memora.org", "password": "demo1234"}
    )

    assert response.status_code == 401


def test_clinical_login_requires_email_and_password():
    response = client.post("/auth/clinical", json={"email": "dr.sharma@memora.org"})

    assert response.status_code == 422


# --- logout -----------------------------------------------------------------


def test_logout_invalidates_the_token():
    token = client.post(
        "/auth/clinical", json={"email": "dr.sharma@memora.org", "password": "demo1234"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout_response = client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 204

    follow_up = client.get("/patients/CA-1001", headers=headers)
    assert follow_up.status_code == 401


def test_logout_requires_auth():
    response = client.post("/auth/logout")

    assert response.status_code == 401


# --- GET /patients tiering ---------------------------------------------------


def test_unauthenticated_patients_list_returns_minimal_shape():
    response = client.get("/patients")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 11  # demo-patient + 10 seeded mock patients
    assert set(body[0].keys()) == {"id", "name", "preferredLanguage", "age"}


def test_clinician_patients_list_returns_full_shape():
    token = issue_token("clinician", "dr-sharma")

    response = client.get("/patients", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 11
    row = next(p for p in body if p["id"] == "CA-1001")
    assert row["preferredLanguage"] == "Hindi"
    assert row["assessmentCount"] == 0
    assert row["latestAssessment"] is None


def test_clinician_patients_list_language_all_sentinel_is_not_a_filter():
    """Patients.jsx's language <select> sends the literal string "all" for
    its default/unselected option (not an omitted param) -- this must not
    be treated as a literal preferred_language == "all" filter, which
    would match zero patients."""
    token = issue_token("clinician", "dr-sharma")

    response = client.get(
        "/patients", params={"language": "all"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 11


def test_clinician_patients_list_filters_by_real_language():
    token = issue_token("clinician", "dr-sharma")

    response = client.get(
        "/patients", params={"language": "Hindi"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert [p["id"] for p in body] == ["CA-1001"]


def test_participant_token_still_gets_minimal_patients_shape():
    token = issue_token("participant", "CA-1001")

    response = client.get("/patients", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "assessmentCount" not in response.json()[0]


# --- GET /patients/{id}/assessments -----------------------------------------


def test_patient_assessments_404_for_unknown_patient():
    token = issue_token("clinician", "dr-sharma")

    response = client.get(
        "/patients/not-a-real-id/assessments", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_patient_assessments_requires_auth():
    response = client.get("/patients/CA-1001/assessments")

    assert response.status_code == 401
