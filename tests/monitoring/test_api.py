import pytest
from fastapi.testclient import TestClient

from backend.main import app

raw_client = TestClient(app)


@pytest.fixture
def client(clinician_headers):
    # Same app, but every request carries a clinician bearer token.
    c = TestClient(app)
    c.headers.update(clinician_headers)
    return c


def test_status_works_and_lists_what_is_missing(client):
    body = client.get("/monitoring/status").json()
    assert set(body) == {"live_camera", "counters", "state"}
    assert isinstance(body["live_camera"]["missing"], list)


def test_alerts_empty_at_first(client):
    assert client.get("/monitoring/alerts").json() == []


def test_observation_empty_at_first(client):
    assert client.get("/monitoring/observation").json() == {}


def test_post_observation_returns_alerts_and_they_are_listed(client):
    r = client.post(
        "/monitoring/observations",
        json={"person_present": True, "fall_in_progress": True, "patient_id": "demo-patient"},
    )
    assert r.status_code == 201
    assert r.json()[0]["kind"] == "fall_event"
    listed = client.get("/monitoring/alerts", params={"patient_id": "demo-patient"}).json()
    assert [a["kind"] for a in listed] == ["fall_event"]
    assert client.get("/monitoring/alerts", params={"patient_id": "someone-else"}).json() == []


def test_post_observation_accepts_empty_body_and_ignores_unknown_keys(client):
    r = client.post("/monitoring/observations", json={"_raw": "x", "whatever": 1})
    assert r.status_code == 201 and r.json() == []


def test_post_observation_rejects_bad_types(client):
    r = client.post("/monitoring/observations", json={"appliances": [{"name": "stove", "state": "maybe"}]})
    assert r.status_code == 422


def test_frame_endpoint_without_camera_stack_returns_json_not_500(client, monkeypatch):
    from monitoring import service as service_module

    monkeypatch.setattr(
        service_module, "live_camera_support",
        lambda: {"available": False, "missing": ["torch", "transformers"]},
    )
    r = client.post("/monitoring/frame", files={"frame": ("f.jpg", b"xx", "image/jpeg")})
    assert r.status_code == 200
    assert r.json() == {"status": "unavailable", "missing": ["torch", "transformers"]}


def test_demo_and_clear(client):
    r = client.post("/monitoring/demo", params={"patient_id": "demo-patient"})
    assert r.status_code == 201
    kinds = {a["kind"] for a in r.json()}
    assert {"unattended_heat_stove", "fall_event"} <= kinds
    assert all(a["source"] == "demo" for a in client.get("/monitoring/alerts").json())
    assert client.delete("/monitoring/demo").json()["deleted"] == len(r.json())
    assert client.get("/monitoring/alerts").json() == []


def test_alerts_limit_is_clamped(client):
    assert client.get("/monitoring/alerts", params={"limit": 100000}).status_code == 200
    assert client.get("/monitoring/alerts", params={"limit": -5}).status_code == 200


def test_assessment_endpoints_still_work_alongside_monitoring(participant_headers):
    assert raw_client.get("/health").json() == {"status": "ok"}
    r = raw_client.post(
        "/assessments",
        json={"patient_id": "CA-1001", "language": "en", "task_id": "cookie-theft"},
        headers=participant_headers,
    )
    assert r.status_code == 201


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/monitoring/status"),
        ("get", "/monitoring/alerts"),
        ("get", "/monitoring/observation"),
        ("post", "/monitoring/observations"),
        ("post", "/monitoring/demo"),
        ("delete", "/monitoring/demo"),
    ],
)
def test_monitoring_requires_login(method, path):
    assert getattr(raw_client, method)(path).status_code == 401


def test_participants_cannot_read_monitoring_data(participant_headers):
    r = raw_client.get("/monitoring/alerts", headers=participant_headers)
    assert r.status_code in (401, 403)


def test_scenarios_are_listed(client):
    ids = [s["id"] for s in client.get("/monitoring/scenarios").json()]
    assert ids[0] == "kitchen_fall" and "night_wandering" in ids


def test_demo_scenario_for_a_patient_is_filterable(client):
    r = client.post("/monitoring/demo", params={"patient_id": "demo-patient", "scenario": "night_wandering"})
    assert r.status_code == 201
    assert all(a["scenario"] == "night_wandering" for a in r.json())
    listed = client.get("/monitoring/alerts", params={"patient_id": "demo-patient"}).json()
    assert {a["kind"] for a in listed} >= {"night_door_open"}


def test_demo_rejects_unknown_scenario_and_patient(client):
    assert client.post("/monitoring/demo", params={"scenario": "nope"}).status_code == 404
    assert client.post("/monitoring/demo", params={"patient_id": "nobody"}).status_code == 404


def test_scenarios_require_clinician():
    assert raw_client.get("/monitoring/scenarios").status_code == 401
