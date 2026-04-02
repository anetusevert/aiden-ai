"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test that /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    """Test that / returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
