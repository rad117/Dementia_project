from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_describes_the_service_instead_of_404():
    from fastapi.testclient import TestClient

    from backend.main import app

    body = TestClient(app).get("/").json()
    assert body["service"] == "Memora API" and body["docs"] == "/docs"
