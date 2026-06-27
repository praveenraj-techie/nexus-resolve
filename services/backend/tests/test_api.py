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


def test_scenarios_endpoint_returns_all_catalog_items():
    client = TestClient(app)
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert len(scenarios) == 11
    assert {scenario["scenario_id"] for scenario in scenarios} >= {
        "disk-space",
        "db-connection-pool",
        "cloud-vm-unhealthy",
    }


def test_unknown_replay_scenario_returns_404():
    client = TestClient(app)
    response = client.get("/api/replay/not-a-scenario")

    assert response.status_code == 404


def test_servicenow_mock_connector_returns_synthetic_ticket_shape():
    client = TestClient(app)
    response = client.get("/api/connectors/servicenow/mock-ticket/disk-space")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connector"] == "servicenow-mock"
    assert payload["synthetic_only"] is True
    assert payload["record"]["number"] == "INC-2026-00421"
    assert payload["record"]["cmdb_ci"] == "APP-WIN-042"


def test_policy_demo_block_endpoint_shows_protected_path_block():
    client = TestClient(app)
    response = client.get("/api/policy/demo-block")

    assert response.status_code == 200
    checks = response.json()["checks"]
    assert any(
        check["name"] == "Target scope" and check["status"] == "blocked"
        for check in checks
    )


def test_audit_packet_endpoint_returns_hash_and_safety_metadata():
    client = TestClient(app)
    started = client.post("/api/incidents", json={"scenario_id": "disk-space"})
    assert started.status_code == 200

    run_id = started.json()["run_id"]
    response = client.get(f"/api/runs/{run_id}/audit-packet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["audit_hash"].startswith("sha256:")
    assert payload["safety"]["synthetic_only"] is True
    assert payload["packet"]["run_id"] == run_id
