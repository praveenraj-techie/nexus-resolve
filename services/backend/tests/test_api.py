from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_replay_endpoint_returns_events():
    client = TestClient(app)
    response = client.get("/api/replay/disk-space")

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) >= 10
    assert events[0]["type"] == "ticket.received"


def test_policy_demo_block_endpoint_shows_protected_path_block():
    client = TestClient(app)
    response = client.get("/api/policy/demo-block")

    assert response.status_code == 200
    checks = response.json()["checks"]
    assert any(
        check["name"] == "Protected paths" and check["status"] == "blocked"
        for check in checks
    )

