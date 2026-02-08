"""Unit tests for Bearer token authentication."""

import pytest
from fastapi.testclient import TestClient


class TestBearerTokenAuth:
    """Test suite for Bearer token authentication on POST /tasks/."""

    def test_create_task_with_valid_token(self, client: TestClient, auth_headers: dict):
        """Test that POST /tasks/ works with valid Bearer token."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Test Task",
                "interval_minutes": 10.0,
                "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
            },
            headers=auth_headers,
        )
        data = response.json()

        assert response.status_code == 200
        assert data["name"] == "Test Task"
        assert "id" in data

    def test_create_task_without_token_returns_401(self, client: TestClient):
        """Test that POST /tasks/ returns 401 without authentication."""
        response = client.post(
            "/tasks/", json={"name": "Test Task", "interval_minutes": 10.0}
        )

        assert response.status_code == 401

    def test_create_task_with_invalid_token_returns_401(self, client: TestClient):
        """Test that POST /tasks/ returns 401 with invalid token."""
        response = client.post(
            "/tasks/",
            json={"name": "Test Task", "interval_minutes": 10.0},
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing token"

    def test_create_task_with_wrong_auth_scheme(self, client: TestClient):
        """Test that POST /tasks/ fails with wrong auth scheme (Basic)."""
        response = client.post(
            "/tasks/",
            json={"name": "Test Task", "interval_minutes": 10.0},
            headers={"Authorization": "Basic secret-token-123"},
        )

        assert response.status_code == 401

    def test_create_task_with_malformed_bearer_header(self, client: TestClient):
        """Test that POST /tasks/ fails with malformed Bearer header."""
        response = client.post(
            "/tasks/",
            json={"name": "Test Task", "interval_minutes": 10.0},
            headers={"Authorization": "Bearer"},  # Missing token
        )

        assert response.status_code == 401

    def test_get_tasks_does_not_require_auth(self, client: TestClient):
        """Test that GET /tasks/ doesn't require authentication."""
        response = client.get("/tasks/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_notifications_does_not_require_auth(self, client: TestClient):
        """Test that GET /notifications/ doesn't require authentication."""
        response = client.get("/notifications/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_auth_header_has_www_authenticate_on_401(self, client: TestClient):
        """Test that 401 responses include WWW-Authenticate header."""
        response = client.post(
            "/tasks/",
            json={"name": "Test Task", "interval_minutes": 10.0},
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert response.status_code == 401
        assert "www-authenticate" in response.headers
        assert "Bearer" in response.headers["www-authenticate"]
