"""Tests for phase validation on task creation (Task #16).

Validates that tasks must have at least one phase when created via POST /tasks/.
"""

import pytest
from fastapi.testclient import TestClient


class TestPhaseValidation:
    """PV-001 to PV-008: Phase validation tests for task creation."""

    def test_create_task_without_phases_fails(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-001: Task creation fails when phases is an empty list."""
        task_data = {"name": "Task Without Phases", "priority": "medium", "phases": []}

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 400
        assert "at least one phase" in response.json()["detail"].lower()

    def test_create_task_with_missing_phases_field_fails(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-002: Task creation fails when phases field is missing."""
        task_data = {"name": "Task with missing phases field", "priority": "medium"}

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_task_with_single_phase_succeeds(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-003: Task creation succeeds with at least one phase."""
        task_data = {
            "name": "Task With One Phase",
            "priority": "medium",
            "phases": [
                {
                    "name": "Initial Phase",
                    "status": "not_started",
                    "order": 1,
                    "todos": [{"name": "First Todo", "status": "todo"}],
                }
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Task With One Phase"
        assert len(data["phases"]) == 1
        assert data["phases"][0]["name"] == "Initial Phase"

    def test_create_task_with_multiple_phases_succeeds(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-004: Task creation succeeds with multiple phases."""
        task_data = {
            "name": "Task With Multiple Phases",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "not_started",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "todo"}],
                },
                {
                    "name": "Phase 2",
                    "status": "not_started",
                    "order": 2,
                    "todos": [{"name": "Todo 2", "status": "todo"}],
                },
                {
                    "name": "Phase 3",
                    "status": "not_started",
                    "order": 3,
                    "todos": [{"name": "Todo 3", "status": "todo"}],
                },
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Task With Multiple Phases"
        assert len(data["phases"]) == 3

    def test_error_message_for_empty_phases(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-005: Error message is clear and helpful when phases are empty."""
        task_data = {"name": "Invalid Task", "phases": []}

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "at least one phase" in error_detail.lower()
        assert "required" in error_detail.lower()

    def test_phase_without_todos_fails(self, client: TestClient, auth_headers: dict):
        """PV-006: Task creation fails when a phase has no todos."""
        task_data = {
            "name": "Task With Empty Phase",
            "phases": [
                {
                    "name": "Empty Phase",
                    "status": "not_started",
                    "order": 1,
                    "todos": [],
                }
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 400
        assert "at least one todo" in response.json()["detail"].lower()

    def test_multiple_phases_all_need_todos(
        self, client: TestClient, auth_headers: dict
    ):
        """PV-007: All phases must have at least one todo."""
        task_data = {
            "name": "Task With Mixed Phases",
            "phases": [
                {
                    "name": "Good Phase",
                    "status": "not_started",
                    "order": 1,
                    "todos": [{"name": "Good Todo", "status": "todo"}],
                },
                {"name": "Bad Phase", "status": "not_started", "order": 2, "todos": []},
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert (
            "bad phase" in error_detail.lower()
            or "at least one todo" in error_detail.lower()
        )

    def test_unauthorized_task_creation_fails(self, client: TestClient):
        """PV-008: Task creation without auth token should fail."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Unauthorized task",
                "phases": [{"name": "Phase 1", "todos": [{"name": "Todo 1"}]}],
            },
        )
        assert response.status_code == 401 or response.status_code == 403


class TestPhaseValidationEdgeCases:
    """Edge case tests for phase validation."""

    def test_create_task_with_whitespace_phase_name(
        self, client: TestClient, auth_headers: dict
    ):
        """Phase with only whitespace in name should be handled."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with whitespace phase",
                "priority": "medium",
                "phases": [
                    {
                        "name": "   ",  # Whitespace only
                        "description": "Test",
                        "status": "not_started",
                        "order": 1,
                        "todos": [{"name": "Todo 1", "status": "todo"}],
                    }
                ],
            },
            headers=auth_headers,
        )
        # Should succeed (we're not validating phase names yet)
        assert response.status_code == 200

    def test_create_task_with_whitespace_todo_name(
        self, client: TestClient, auth_headers: dict
    ):
        """Todo with only whitespace in name should be handled."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with whitespace todo",
                "priority": "medium",
                "phases": [
                    {
                        "name": "Phase 1",
                        "description": "Test",
                        "status": "not_started",
                        "order": 1,
                        "todos": [
                            {"name": "   ", "status": "todo"}  # Whitespace only
                        ],
                    }
                ],
            },
            headers=auth_headers,
        )
        # Should succeed (we're not validating todo names yet)
        assert response.status_code == 200

    def test_create_task_with_very_long_names(
        self, client: TestClient, auth_headers: dict
    ):
        """Task with very long names should succeed."""
        long_name = "A" * 1000
        response = client.post(
            "/tasks/",
            json={
                "name": long_name,
                "priority": "medium",
                "phases": [
                    {
                        "name": long_name,
                        "description": long_name,
                        "status": "not_started",
                        "order": 1,
                        "todos": [
                            {
                                "name": long_name,
                                "description": long_name,
                                "status": "todo",
                            }
                        ],
                    }
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_create_task_with_special_characters(
        self, client: TestClient, auth_headers: dict
    ):
        """Task with special characters in names should succeed."""
        special_name = "Task <>&\"'特殊字符🎉"
        response = client.post(
            "/tasks/",
            json={
                "name": special_name,
                "priority": "medium",
                "phases": [
                    {
                        "name": special_name,
                        "description": special_name,
                        "status": "not_started",
                        "order": 1,
                        "todos": [
                            {
                                "name": special_name,
                                "description": special_name,
                                "status": "todo",
                            }
                        ],
                    }
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == special_name
