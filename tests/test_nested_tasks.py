"""Tests for nested task structure (Tasks -> Phases -> Todos + Comments)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime, timezone

from main import (
    Task,
    Phase,
    Todo,
    Comment,
    calculate_task_progress,
    recalculate_task_progress,
)


@pytest.fixture(name="sample_task_with_phases")
def sample_task_with_phases_fixture(client: TestClient, auth_headers: dict):
    """Create a sample task with nested phases and todos."""
    task_data = {
        "name": "Project Alpha",
        "description": "Major feature implementation",
        "priority": "high",
        "due_date": "2026-03-01T00:00:00Z",
        "flow_chart": "graph TD; A[Start] --> B[Phase 1];",
        "context_tags": "backend,api,critical",
        "definition_of_done": "All phases complete",
        "phases": [
            {
                "name": "Planning",
                "status": "completed",
                "order": 1,
                "todos": [
                    {"name": "Define requirements", "status": "done"},
                    {"name": "Create wireframes", "status": "done"},
                ],
            },
            {
                "name": "Development",
                "status": "in_progress",
                "order": 2,
                "todos": [
                    {"name": "Setup project", "status": "done"},
                    {"name": "Implement API", "status": "in_progress"},
                    {"name": "Write tests", "status": "todo"},
                ],
            },
        ],
    }

    response = client.post("/tasks/", json=task_data, headers=auth_headers)
    assert response.status_code == 200
    return response.json()


# ============================================================================
# TESTS: Create Task with Nested Structure
# ============================================================================


class TestCreateTaskWithNestedStructure:
    """T-001: Create task with nested phases."""

    def test_create_task_with_phases(self, client: TestClient, auth_headers: dict):
        """Test creating a task with phases and todos."""
        task_data = {
            "name": "Simple Project",
            "priority": "medium",
            "phases": [
                {
                    "name": "Phase 1", 
                    "status": "not_started", 
                    "order": 1,
                    "todos": [{"name": "Todo 1"}]
                },
                {
                    "name": "Phase 2", 
                    "status": "not_started", 
                    "order": 2,
                    "todos": [{"name": "Todo 2"}]
                },
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()

        assert response.status_code == 200
        assert data["name"] == "Simple Project"
        assert data["priority"] == "medium"
        assert len(data["phases"]) == 2
        assert data["phases"][0]["name"] == "Phase 1"
        assert data["phases"][1]["name"] == "Phase 2"
        assert data["progress_percent"] == 0

    def test_create_task_with_phases_and_todos(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """T-002: Full nested creation with phases and todos."""
        data = sample_task_with_phases

        assert data["name"] == "Project Alpha"
        assert data["description"] == "Major feature implementation"
        assert data["priority"] == "high"
        assert len(data["phases"]) == 2

        # Check first phase
        phase1 = data["phases"][0]
        assert phase1["name"] == "Planning"
        assert phase1["status"] == "completed"
        assert len(phase1["todos"]) == 2
        assert phase1["todos"][0]["name"] == "Define requirements"

        # Check second phase
        phase2 = data["phases"][1]
        assert phase2["name"] == "Development"
        assert phase2["status"] == "in_progress"
        assert len(phase2["todos"]) == 3

        # Progress should be calculated (1 completed phase + 1/3 of second phase) / 2 = ~67%
        assert data["progress_percent"] > 0

    def test_create_task_without_phases(self, client: TestClient, auth_headers: dict):
        """E-001: Create task with empty phases list fails validation."""
        task_data = {"name": "Empty Task", "priority": "low", "phases": []}

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()

        assert response.status_code == 400
        assert "at least one phase" in data["detail"].lower()


# ============================================================================
# TESTS: Read Task with Hierarchy
# ============================================================================


class TestReadTaskWithHierarchy:
    """T-003: GET returns full nested data."""

    def test_read_task_with_hierarchy(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """Test retrieving a task with full hierarchy."""
        task_id = sample_task_with_phases["id"]

        response = client.get(f"/tasks/{task_id}")
        data = response.json()

        assert response.status_code == 200
        assert data["id"] == task_id
        assert data["name"] == "Project Alpha"
        assert len(data["phases"]) == 2
        assert len(data["phases"][0]["todos"]) == 2
        assert len(data["phases"][1]["todos"]) == 3
        assert "comments" in data

    def test_read_all_tasks_with_hierarchy(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """Test retrieving all tasks with hierarchy."""
        response = client.get("/tasks/")
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["name"] == "Project Alpha"
        assert len(data[0]["phases"]) == 2


# ============================================================================
# TESTS: Update Todo Status
# ============================================================================


class TestUpdateTodoStatus:
    """T-004, T-005: PATCH /todos/{id} and progress updates."""

    def test_update_todo_status(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """Test updating a todo's status."""
        # Get a todo from the sample task
        todo_id = sample_task_with_phases["phases"][1]["todos"][2][
            "id"
        ]  # "Write tests" todo

        response = client.patch(
            f"/todos/{todo_id}", json={"status": "in_progress"}, headers=auth_headers
        )
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "in_progress"
        assert data["name"] == "Write tests"

    def test_update_todo_triggers_progress_update(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """T-005: Progress auto-calculated when todo is updated."""
        task_id = sample_task_with_phases["id"]
        initial_progress = sample_task_with_phases["progress_percent"]

        # Complete the remaining todo
        todo_id = sample_task_with_phases["phases"][1]["todos"][2]["id"]
        client.patch(f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers)

        # Check that progress increased
        response = client.get(f"/tasks/{task_id}")
        data = response.json()

        # All todos in Development phase should now be done
        # Progress should be 50% (Planning) + 50% (Development complete) = 100%
        assert data["progress_percent"] > initial_progress


# ============================================================================
# TESTS: Update Phase Status
# ============================================================================


class TestUpdatePhaseStatus:
    """T-006: PATCH /phases/{id} works."""

    def test_update_phase_status(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """Test updating a phase's status."""
        phase_id = sample_task_with_phases["phases"][1]["id"]  # Development phase

        response = client.patch(
            f"/phases/{phase_id}", json={"status": "completed"}, headers=auth_headers
        )
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "completed"

    def test_phase_completion_updates_task_progress(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """T-006/P-003: Phase completion updates task progress."""
        task_id = sample_task_with_phases["id"]
        phase_id = sample_task_with_phases["phases"][1]["id"]

        # Mark Development phase as completed
        client.patch(
            f"/phases/{phase_id}", json={"status": "completed"}, headers=auth_headers
        )

        # Check task progress
        response = client.get(f"/tasks/{task_id}")
        data = response.json()

        # Both phases should now contribute 50% each = 100%
        assert data["progress_percent"] == 100


# ============================================================================
# TESTS: Comments
# ============================================================================


class TestComments:
    """T-007, T-008: Comments endpoints."""

    def test_create_comment(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """T-007: POST /tasks/{id}/comments works."""
        task_id = sample_task_with_phases["id"]

        response = client.post(
            f"/tasks/{task_id}/comments",
            json={"text": "Great progress!", "author": "user"},
            headers=auth_headers,
        )
        data = response.json()

        assert response.status_code == 200
        assert data["text"] == "Great progress!"
        assert data["author"] == "user"
        assert data["task_id"] == task_id
        assert "timestamp" in data

    def test_comments_included_in_task(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """T-008: Comments returned with task."""
        task_id = sample_task_with_phases["id"]

        # Create a comment
        client.post(
            f"/tasks/{task_id}/comments",
            json={"text": "Test comment", "author": "agent"},
            headers=auth_headers,
        )

        # Get task and verify comment is included
        response = client.get(f"/tasks/{task_id}")
        data = response.json()

        assert len(data["comments"]) >= 1  # At least the system comment from creation
        comment_texts = [c["text"] for c in data["comments"]]
        assert "Test comment" in comment_texts

    def test_get_comments_endpoint(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """Test GET /tasks/{id}/comments endpoint."""
        task_id = sample_task_with_phases["id"]

        # Create a comment
        client.post(
            f"/tasks/{task_id}/comments",
            json={"text": "Another comment", "author": "user"},
            headers=auth_headers,
        )

        response = client.get(f"/tasks/{task_id}/comments")
        data = response.json()

        assert response.status_code == 200
        assert isinstance(data, list)
        assert len(data) >= 1


# ============================================================================
# TESTS: Progress Calculation
# ============================================================================


class TestProgressCalculation:
    """P-001, P-002, P-004, P-006: Progress calculation logic."""

    def test_task_progress_calculation_accuracy(
        self, client: TestClient, auth_headers: dict
    ):
        """P-004: Progress math is correct."""
        # Create a task with 2 phases, 2 todos each
        task_data = {
            "name": "Progress Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "completed",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1", "status": "done"},
                        {"name": "Todo 2", "status": "done"},
                    ],
                },
                {
                    "name": "Phase 2",
                    "status": "in_progress",
                    "order": 2,
                    "todos": [
                        {"name": "Todo 3", "status": "done"},
                        {"name": "Todo 4", "status": "todo"},
                    ],
                },
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()

        # Phase 1: 100% of 50% = 50%
        # Phase 2: 50% of 50% = 25%
        # Total: 75%
        assert data["progress_percent"] == 75

    def test_blocked_phase_contributes_zero(
        self, client: TestClient, auth_headers: dict
    ):
        """P-006: Blocked phases contribute 0 to progress."""
        task_data = {
            "name": "Blocked Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "completed",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "done"}],
                },
                {
                    "name": "Phase 2",
                    "status": "blocked",
                    "order": 2,
                    "todos": [{"name": "Todo 2", "status": "done"}],
                },
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()

        # Only Phase 1 contributes (50% of total)
        assert data["progress_percent"] == 50

    def test_all_todos_done_completes_phase(
        self, client: TestClient, auth_headers: dict
    ):
        """P-002: All todos done should auto-complete phase."""
        task_data = {
            "name": "Auto-complete Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "in_progress",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1", "status": "done"},
                        {"name": "Todo 2", "status": "done"},
                    ],
                }
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()

        # Phase should be auto-completed
        assert data["phases"][0]["status"] == "completed"
        assert data["progress_percent"] == 100


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """E-001 to E-006: Edge case tests."""

    def test_create_phase_without_todos(self, client: TestClient, auth_headers: dict):
        """E-002: Create phase with empty todos list fails."""
        task_data = {
            "name": "Phase without Todos",
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

    def test_progress_with_no_phases(self, client: TestClient, auth_headers: dict):
        """E-003: Task creation fails with no phases."""
        task_data = {"name": "No Phases", "phases": []}

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        assert response.status_code == 400

    def test_progress_with_no_todos(self, client: TestClient, auth_headers: dict):
        """E-004: Task creation fails with phase but no todos."""
        task_data = {
            "name": "No Todos",
            "phases": [
                {
                    "name": "Empty Phase",
                    "status": "in_progress",
                    "order": 1,
                    "todos": [],
                }
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        assert response.status_code == 400

    def test_update_todo_not_found(self, client: TestClient, auth_headers: dict):
        """Test updating non-existent todo."""
        response = client.patch(
            "/todos/99999", json={"status": "done"}, headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_phase_not_found(self, client: TestClient, auth_headers: dict):
        """Test updating non-existent phase."""
        response = client.patch(
            "/phases/99999", json={"status": "completed"}, headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_comment_task_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Test creating comment for non-existent task."""
        response = client.post(
            "/tasks/99999/comments",
            json={"text": "Test", "author": "user"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ============================================================================
# TESTS: Direct Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Direct tests for helper functions."""

    def test_calculate_task_progress_no_task(self, session: Session):
        """Test progress calculation for non-existent task."""
        result = calculate_task_progress(99999, session)
        assert result == 0

    def test_recalculate_task_progress(
        self, client: TestClient, auth_headers: dict, session: Session
    ):
        """Test manual progress recalculation."""
        # Create a task
        task_data = {
            "name": "Recalc Test",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "in_progress",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "todo"}],
                }
            ],
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        task_id = response.json()["id"]

        # Initial progress should be 0
        assert response.json()["progress_percent"] == 0

        # Complete the todo
        todo_id = response.json()["phases"][0]["todos"][0]["id"]
        client.patch(f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers)

        # Recalculate progress
        recalculate_task_progress(task_id, session)

        # Verify progress updated
        task = session.get(Task, task_id)
        assert task.progress_percent == 100


# ============================================================================
# TESTS: System Comments
# ============================================================================


class TestSystemComments:
    """P-005: System comments on status changes."""

    def test_system_comment_on_todo_status_change(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """P-005: Auto-comment created when todo status changes."""
        task_id = sample_task_with_phases["id"]
        todo_id = sample_task_with_phases["phases"][1]["todos"][0]["id"]

        # Update todo status
        client.patch(f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers)

        # Check comments
        response = client.get(f"/tasks/{task_id}/comments")
        comments = response.json()

        # Should have creation comment and status change comment
        comment_texts = [c["text"] for c in comments]
        assert any("status changed" in text.lower() for text in comment_texts)

    def test_system_comment_on_phase_status_change(
        self, client: TestClient, auth_headers: dict, sample_task_with_phases: dict
    ):
        """P-005: Auto-comment created when phase status changes."""
        task_id = sample_task_with_phases["id"]
        phase_id = sample_task_with_phases["phases"][1]["id"]

        # Update phase status
        client.patch(
            f"/phases/{phase_id}", json={"status": "completed"}, headers=auth_headers
        )

        # Check comments
        response = client.get(f"/tasks/{task_id}/comments")
        comments = response.json()

        # Should have phase status change comment
        comment_texts = [c["text"] for c in comments]
        assert any(
            "phase" in text.lower() and "status changed" in text.lower()
            for text in comment_texts
        )

    def test_system_comment_on_task_creation(
        self, client: TestClient, auth_headers: dict
    ):
        """Test that system comment is created when task is created."""
        task_data = {
            "name": "Comment Test Task", 
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}]
        }

        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        data = response.json()
        assert response.status_code == 200
        task_id = data["id"]

        # Check comments
        response = client.get(f"/tasks/{task_id}/comments")
        comments = response.json()

        # Should have creation comment
        assert len(comments) >= 1
        assert any("created" in c["text"].lower() for c in comments)


class TestStatusSync:
    def test_task_status_syncs_with_progress(
        self, client: TestClient, auth_headers: dict
    ):
        """Verify that task.status syncs with progress (todo -> in_progress -> done)."""
        task_data = {
            "name": "Sync Test Task",
            "phases": [
                {
                    "name": "Phase 1",
                    "todos": [
                        {"name": "Todo 1", "status": "todo"},
                        {"name": "Todo 2", "status": "todo"},
                    ],
                }
            ],
        }
        response = client.post("/tasks/", json=task_data, headers=auth_headers)
        task = response.json()
        task_id = task["id"]

        # Initial state (0% progress)
        assert task["status"] == "todo"
        assert task["progress_percent"] == 0

        # Move to 50% progress
        todo_id = task["phases"][0]["todos"][0]["id"]
        client.patch(f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers)

        response = client.get(f"/tasks/{task_id}")
        assert response.json()["progress_percent"] == 50
        assert response.json()["status"] == "in_progress"

        # Move to 100% progress
        todo_id2 = task["phases"][0]["todos"][1]["id"]
        client.patch(
            f"/todos/{todo_id2}", json={"status": "done"}, headers=auth_headers
        )

        response = client.get(f"/tasks/{task_id}")
        assert response.json()["progress_percent"] == 100
        assert response.json()["status"] == "done"
