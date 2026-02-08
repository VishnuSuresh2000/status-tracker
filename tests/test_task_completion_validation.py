import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from main import app, get_session, Task, Phase, Todo


# Setup test database
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(monkeypatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "test-token")
    return {"Authorization": "Bearer test-token"}


class TestTaskCompletionValidation:
    """Tests for hard block validation when marking tasks as done."""

    def test_task_with_all_todos_done_can_be_completed(
        self, client, session, auth_headers
    ):
        """Test that a task with all todos done can be marked as done."""
        # Create task with phase and todos
        task = Task(name="Complete Task", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Phase 1", status="in_progress")
        session.add(phase)
        session.commit()
        session.refresh(phase)

        todo1 = Todo(phase_id=phase.id, name="Todo 1", status="done")
        todo2 = Todo(phase_id=phase.id, name="Todo 2", status="done")
        session.add(todo1)
        session.add(todo2)
        session.commit()

        # Mark task as done - should succeed
        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_task_with_incomplete_todos_blocked(self, client, session, auth_headers):
        """Test that a task with incomplete todos is blocked from being marked done."""
        # Create task with phase and todos
        task = Task(name="Incomplete Task", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Phase 1", status="in_progress")
        session.add(phase)
        session.commit()
        session.refresh(phase)

        todo1 = Todo(phase_id=phase.id, name="Todo 1", status="done")
        todo2 = Todo(phase_id=phase.id, name="Todo 2", status="todo")
        session.add(todo1)
        session.add(todo2)
        session.commit()

        # Try to mark task as done - should be blocked with 409
        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 409
        assert "Cannot mark task as done" in response.json()["detail"]
        assert "1 of 2 checklist items remain incomplete" in response.json()["detail"]
        assert "Phase 1" in response.json()["detail"]

    def test_task_with_no_phases_allowed(self, client, session, auth_headers):
        """Test that a task with no phases can be marked as done."""
        task = Task(name="No Phases Task", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_task_with_empty_phases_allowed(self, client, session, auth_headers):
        """Test that a task with empty phases (no todos) can be marked as done."""
        task = Task(name="Empty Phase Task", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Empty Phase", status="not_started")
        session.add(phase)
        session.commit()

        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_changing_from_done_to_other_status_allowed(
        self, client, session, auth_headers
    ):
        """Test that changing from done to other status is allowed without validation."""
        task = Task(name="Reopen Task", status="done", progress_percent=100)
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Phase 1", status="completed")
        session.add(phase)
        session.commit()
        session.refresh(phase)

        # Add incomplete todo - shouldn't matter when changing FROM done
        todo = Todo(phase_id=phase.id, name="Todo 1", status="todo")
        session.add(todo)
        session.commit()

        # Change from done to in_progress - should succeed
        response = client.patch(
            f"/tasks/{task.id}", params={"status": "in_progress"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_multiple_phases_with_incomplete_items_blocked(
        self, client, session, auth_headers
    ):
        """Test that incomplete items in multiple phases are all reported."""
        task = Task(name="Multi Phase Task", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        phase1 = Phase(task_id=task.id, name="Setup Phase", status="in_progress")
        phase2 = Phase(
            task_id=task.id, name="Implementation Phase", status="in_progress"
        )
        session.add(phase1)
        session.add(phase2)
        session.commit()
        session.refresh(phase1)
        session.refresh(phase2)

        # Phase 1: 1 done, 1 todo
        todo1 = Todo(phase_id=phase1.id, name="Setup Todo 1", status="done")
        todo2 = Todo(phase_id=phase1.id, name="Setup Todo 2", status="todo")
        session.add(todo1)
        session.add(todo2)

        # Phase 2: 0 done, 2 todo
        todo3 = Todo(phase_id=phase2.id, name="Impl Todo 1", status="todo")
        todo4 = Todo(phase_id=phase2.id, name="Impl Todo 2", status="todo")
        session.add(todo3)
        session.add(todo4)
        session.commit()

        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 409
        error_detail = response.json()["detail"]
        assert "3 of 4 checklist items remain incomplete" in error_detail
        assert "Setup Phase" in error_detail
        assert "Implementation Phase" in error_detail

    def test_task_already_done_no_validation_needed(
        self, client, session, auth_headers
    ):
        """Test that updating a task already marked done doesn't trigger validation."""
        task = Task(name="Already Done", status="done", progress_percent=100)
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Phase 1", status="completed")
        session.add(phase)
        session.commit()
        session.refresh(phase)

        # Incomplete todo
        todo = Todo(phase_id=phase.id, name="Todo 1", status="todo")
        session.add(todo)
        session.commit()

        # Mark as done again - should succeed (no validation for already done)
        response = client.patch(
            f"/tasks/{task.id}", params={"status": "done"}, headers=auth_headers
        )
        assert response.status_code == 200

    def test_progress_percent_update_without_status_change(
        self, client, session, auth_headers
    ):
        """Test that updating only progress_percent doesn't trigger validation."""
        task = Task(name="Progress Update", status="in_progress")
        session.add(task)
        session.commit()
        session.refresh(task)

        phase = Phase(task_id=task.id, name="Phase 1", status="in_progress")
        session.add(phase)
        session.commit()
        session.refresh(phase)

        # Incomplete todo
        todo = Todo(phase_id=phase.id, name="Todo 1", status="todo")
        session.add(todo)
        session.commit()

        # Update progress only - should succeed
        response = client.patch(
            f"/tasks/{task.id}", params={"progress_percent": 50}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["progress_percent"] == 50
