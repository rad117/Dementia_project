from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_status_works_and_lists_what_is_missing():
    body = client.get("/monitoring/status").json()
    assert set(body) == {"live_camera", "counters", "state"}
    assert isinstance(body["live_camera"]["missing"], list)


def test_alerts_empty_at_first():
    assert client.get("/monitoring/alerts").json() == []


def test_observation_empty_at_first():
    assert client.get("/monitoring/observation").json() == {}


def test_post_observation_returns_alerts_and_they_are_listed():
    r = client.post(
        "/monitoring/observations",
        json={"person_present": True, "fall_in_progress": True, "patient_id": "demo-patient"},
    )
    assert r.status_code == 201
    assert r.json()[0]["kind"] == "fall_event"
    listed = client.get("/monitoring/alerts", params={"patient_id": "demo-patient"}).json()
    assert [a["kind"] for a in listed] == ["fall_event"]
    assert client.get("/monitoring/alerts", params={"patient_id": "someone-else"}).json() == []


def test_post_observation_accepts_empty_body_and_ignores_unknown_keys():
    r = client.post("/monitoring/observations", json={"_raw": "x", "whatever": 1})
    assert r.status_code == 201 and r.json() == []


def test_post_observation_rejects_bad_types():
    r = client.post("/monitoring/observations", json={"appliances": [{"name": "stove", "state": "maybe"}]})
    assert r.status_code == 422


def test_frame_endpoint_without_camera_stack_returns_json_not_500(monkeypatch):
    from monitoring import service as service_module

    monkeypatch.setattr(
        service_module, "live_camera_support",
        lambda: {"available": False, "missing": ["torch", "transformers"]},
    )
    r = client.post("/monitoring/frame", files={"frame": ("f.jpg", b"xx", "image/jpeg")})
    assert r.status_code == 200
    assert r.json() == {"status": "unavailable", "missing": ["torch", "transformers"]}


def test_demo_and_clear():
    r = client.post("/monitoring/demo", params={"patient_id": "demo-patient"})
    assert r.status_code == 201
    kinds = {a["kind"] for a in r.json()}
    assert {"unattended_heat_stove", "fall_event"} <= kinds
    assert all(a["source"] == "demo" for a in client.get("/monitoring/alerts").json())
    assert client.delete("/monitoring/demo").json()["deleted"] == len(r.json())
    assert client.get("/monitoring/alerts").json() == []


def test_alerts_limit_is_clamped():
    assert client.get("/monitoring/alerts", params={"limit": 100000}).status_code == 200
    assert client.get("/monitoring/alerts", params={"limit": -5}).status_code == 200


def test_assessment_endpoints_still_work_alongside_monitoring():
    assert client.get("/health").json() == {"status": "ok"}
    r = client.post("/assessments", json={"patient_id": "p", "language": "en", "task_id": "cookie-theft"})
    assert r.status_code == 201
