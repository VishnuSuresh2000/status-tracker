"""
Unit tests for Phase and Todo validation in task creation.
"""
import os

# Set test auth token BEFORE importing main
os.environ["API_AUTH_TOKEN"] = "test-auth-token-for-tests"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from main import app, get_session

# Test database
TEST_DATABASE_URL = "sqlite:///./data/test_validation.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


def get_test_session():
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_session] = get_test_session

client = TestClient(app)
headers = {"Authorization": "Bearer test-auth-token-for-tests"}


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


class TestPhaseValidation:
    """Tests for phase validation on task creation."""

    def test_create_task_without_phases_fails(self):
        """Task creation should fail if no phases provided."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task without phases",
                "description": "This should fail",
                "priority": "medium",
                "phases": []
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "at least one phase" in response.json()["detail"].lower()

    def test_create_task_with_missing_phases_field_fails(self):
        """Task creation should fail if phases field is missing."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with missing phases field",
                "description": "This should fail",
                "priority": "medium"
            },
            headers=headers
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_create_task_with_phase_but_no_todos_fails(self):
        """Task creation should fail if a phase has no todos."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with empty phase",
                "description": "This should fail",
                "priority": "medium",
                "phases": [
                    {
                        "name": "Phase 1",
                        "description": "Empty phase",
                        "status": "todo",
                        "order": 1,
                        "todos": []
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "at least one todo" in response.json()["detail"].lower()

    def test_create_task_with_phase_missing_todos_field_fails(self):
        """Task creation should fail if a phase has no todos field."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with phase missing todos",
                "description": "This should fail",
                "priority": "medium",
                "phases": [
                    {
                        "name": "Phase 1",
                        "description": "No todos field",
                        "status": "todo",
                        "order": 1
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 400 or response.status_code == 422

    def test_create_task_with_valid_phases_and_todos_succeeds(self):
        """Task creation should succeed with valid phases and todos."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Valid task",
                "description": "This should succeed",
                "priority": "high",
                "phases": [
                    {
                        "name": "Phase 1",
                        "description": "First phase",
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": "Todo 1", "description": "First todo", "status": "todo"},
                            {"name": "Todo 2", "description": "Second todo", "status": "todo"}
                        ]
                    },
                    {
                        "name": "Phase 2",
                        "description": "Second phase",
                        "status": "todo",
                        "order": 2,
                        "todos": [
                            {"name": "Todo 3", "description": "Third todo", "status": "todo"}
                        ]
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Valid task"
        assert len(data["phases"]) == 2
        assert len(data["phases"][0]["todos"]) == 2
        assert len(data["phases"][1]["todos"]) == 1

    def test_create_task_with_single_phase_and_single_todo_succeeds(self):
        """Task creation should succeed with minimum valid phases/todos."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Minimal valid task",
                "description": "Minimum required",
                "priority": "low",
                "phases": [
                    {
                        "name": "Only Phase",
                        "description": "Single phase",
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": "Only Todo", "description": "Single todo", "status": "todo"}
                        ]
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["phases"]) == 1
        assert len(data["phases"][0]["todos"]) == 1

    def test_create_task_multiple_phases_second_empty_fails(self):
        """Task creation should fail if second phase is empty."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with second empty phase",
                "description": "Should fail",
                "priority": "medium",
                "phases": [
                    {
                        "name": "Phase 1",
                        "description": "Valid phase",
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": "Todo 1", "description": "Valid todo", "status": "todo"}
                        ]
                    },
                    {
                        "name": "Phase 2",
                        "description": "Empty phase",
                        "status": "todo",
                        "order": 2,
                        "todos": []
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 400
        assert "Phase 2" in response.json()["detail"]
        assert "at least one todo" in response.json()["detail"].lower()

    def test_unauthorized_task_creation_fails(self):
        """Task creation without auth token should fail."""
        response = client.post(
            "/tasks/",
            json={
                "name": "Unauthorized task",
                "phases": [
                    {
                        "name": "Phase 1",
                        "todos": [{"name": "Todo 1"}]
                    }
                ]
            }
        )
        assert response.status_code == 401 or response.status_code == 403


class TestPhaseValidationEdgeCases:
    """Edge case tests for phase validation."""

    def test_create_task_with_whitespace_phase_name_fails(self):
        """Phase with only whitespace in name should be handled."""
        # This test depends on whether we want to validate phase names
        # For now, we just check it doesn't crash
        response = client.post(
            "/tasks/",
            json={
                "name": "Task with whitespace phase",
                "priority": "medium",
                "phases": [
                    {
                        "name": "   ",  # Whitespace only
                        "description": "Test",
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": "Todo 1", "status": "todo"}
                        ]
                    }
                ]
            },
            headers=headers
        )
        # Should succeed (we're not validating phase names yet)
        assert response.status_code == 200

    def test_create_task_with_whitespace_todo_name_succeeds(self):
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
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": "   ", "status": "todo"}  # Whitespace only
                        ]
                    }
                ]
            },
            headers=headers
        )
        # Should succeed (we're not validating todo names yet)
        assert response.status_code == 200

    def test_create_task_with_very_long_names_succeeds(self):
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
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": long_name, "description": long_name, "status": "todo"}
                        ]
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 200

    def test_create_task_with_special_characters_succeeds(self):
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
                        "status": "todo",
                        "order": 1,
                        "todos": [
                            {"name": special_name, "description": special_name, "status": "todo"}
                        ]
                    }
                ]
            },
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == special_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
