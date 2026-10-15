"""
Automated tests for FastAPI endpoints using TestClient.
Tests valid inputs, invalid inputs, candidate status updates, and stats.
"""

from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_root_endpoint():
    """Verify health check / root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_get_job_config():
    """Verify retrieval of job requirements."""
    response = client.get("/api/job")
    assert response.status_code == 200
    data = response.json()
    assert "must_have" in data
    assert "nice_to_have" in data

def test_get_stats():
    """Verify dashboard stats structure."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_screened" in stats
    assert "qualified" in stats
    assert "statuses" in stats

def test_list_candidates_filter():
    """Verify candidates list and filtering logic."""
    response = client.get("/api/candidates?filter_type=all")
    assert response.status_code == 200
    res_data = response.json()
    assert "candidates" in res_data
    assert isinstance(res_data["candidates"], list)

def test_invalid_filter_param():
    """Verify API handles invalid filter parameter with validation error (422)."""
    response = client.get("/api/candidates?filter_type=invalid_filter")
    assert response.status_code == 422

def test_invalid_status_update():
    """Verify updating a candidate with an invalid status fails with 400."""
    response = client.patch(
        "/api/candidates/non_existent_id/status",
        json={"status": "InvalidStatusChoice"}
    )
    assert response.status_code == 400

def test_candidate_not_found():
    """Verify 404 is returned when requesting a non-existent candidate."""
    response = client.get("/api/candidates/definitely_not_a_real_candidate_id_99999")
    assert response.status_code == 404
    
    