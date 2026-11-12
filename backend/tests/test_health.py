from fastapi.testclient import TestClient

from app.main import app


def test_liveness_endpoint_returns_healthy():
    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "check": "liveness"}
    assert response.headers.get("X-Correlation-ID")


def test_correlation_id_is_preserved():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live", headers={"X-Correlation-ID": "test-correlation-123"}
        )
    assert response.headers["X-Correlation-ID"] == "test-correlation-123"


def test_readiness_endpoint_reports_dependency_state():
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert body["check"] == "readiness"
    assert "database" in body["dependencies"]
