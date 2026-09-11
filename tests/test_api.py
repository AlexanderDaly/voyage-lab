from fastapi.testclient import TestClient

from voyage_lab.api import app
from voyage_lab.core import KNOT

client = TestClient(app)


def test_complete_api_comparison_and_replay():
    catalog = client.get("/api/catalog").json()
    response = client.post(
        "/api/compare",
        json={"scenario": catalog["scenario"], "speeds_mps": [10 * KNOT, 12 * KNOT, 14 * KNOT]},
    )
    assert response.status_code == 200, response.text
    bundle = response.json()
    assert len(bundle["runs"]) == 3
    assert len({r["hashes"]["environment"] for r in bundle["runs"]}) == 1
    replay = client.post("/api/replay", json=bundle)
    assert replay.status_code == 200, replay.text
    assert replay.json()["verified"]


def test_invalid_and_failed_runs_are_distinct():
    scenario = client.get("/api/catalog").json()["scenario"]
    invalid = client.post("/api/simulate", json=scenario | {"speed_mps": -1})
    assert invalid.status_code == 422
    scenario["departure"] = "2026-09-22T00:00:00Z"
    scenario["deadline"] = "2026-09-25T00:00:00Z"
    missing = client.post("/api/simulate", json=scenario)
    assert missing.status_code == 200
    assert missing.json()["result"]["status"] == "missing_coverage"


def test_body_limit_and_fixture_allowlist():
    assert client.post("/api/replay", content=b" " * 5_000_001).status_code == 413
    assert client.get("/api/fixtures/nonexistent").status_code == 404


def test_compare_validates_all_speeds():
    scenario = client.get("/api/catalog").json()["scenario"]
    assert (
        client.post("/api/compare", json={"scenario": scenario, "speeds_mps": [10 * KNOT, 50]}).status_code
        == 422
    )
