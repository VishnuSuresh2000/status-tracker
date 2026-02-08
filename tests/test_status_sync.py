import os

# Set test auth token BEFORE importing main
os.environ["API_AUTH_TOKEN"] = "test-auth-token-for-tests"

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from main import app, get_session
import pytest

# Setup in-memory SQLite for testing
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture():
    """Return valid authentication headers for POST /tasks/."""
    return {"Authorization": "Bearer test-auth-token-for-tests"}


def test_task_done_cascades_to_phases_and_todos(client: TestClient, auth_headers: dict):
    """
    Regression test: When a task is marked as 'done', all its phases should be
    marked as 'completed' and all todos should be marked as 'done'.
    Progress should also be set to 100.
    """
    # Create a task with multiple phases and todos in various states
    response = client.post(
        "/tasks/",
        json={
            "name": "Cascading Test Task",
            "priority": "high",
            "phases": [
                {
                    "name": "Phase 1 - Not Started",
                    "status": "not_started",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1.1 - todo", "status": "todo"},
                        {"name": "Todo 1.2 - todo", "status": "todo"},
                    ],
                },
                {
                    "name": "Phase 2 - In Progress",
                    "status": "in_progress",
                    "order": 2,
                    "todos": [
                        {"name": "Todo 2.1 - in_progress", "status": "in_progress"},
                        {"name": "Todo 2.2 - todo", "status": "todo"},
                    ],
                },
                {
                    "name": "Phase 3 - Partially Done",
                    "status": "in_progress",
                    "order": 3,
                    "todos": [
                        {"name": "Todo 3.1 - done", "status": "done"},
                        {"name": "Todo 3.2 - todo", "status": "todo"},
                    ],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    phases = response.json()["phases"]
    initial_progress = response.json()["progress_percent"]

    # Verify initial state shows partial progress
    assert initial_progress < 100

    # First complete all todos (required by validation)
    for phase in phases:
        for todo in phase["todos"]:
            response = client.patch(
                f"/todos/{todo['id']}", json={"status": "done"}, headers=auth_headers
            )
            assert response.status_code == 200

    # Mark the task as done via PATCH endpoint
    response = client.patch(f"/tasks/{task_id}?status=done", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()

    # Verify task is marked as done with 100% progress
    assert data["status"] == "done"
    assert data["progress_percent"] == 100

    # Verify all phases are now completed
    assert len(data["phases"]) == 3
    for phase in data["phases"]:
        assert phase["status"] == "completed", (
            f"Phase '{phase['name']}' should be 'completed' but was '{phase['status']}'"
        )

        # Verify all todos in each phase are done
        for todo in phase["todos"]:
            assert todo["status"] == "done", (
                f"Todo '{todo['name']}' should be 'done' but was '{todo['status']}'"
            )


def test_task_done_with_empty_phases(client: TestClient, auth_headers: dict):
    """
    Test that marking a task as done works when phases have todos that are all done.
    """
    # Create a task with a phase that has todos
    response = client.post(
        "/tasks/",
        json={
            "name": "Task With Complete Phase",
            "priority": "medium",
            "phases": [
                {
                    "name": "Complete Phase",
                    "status": "not_started",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1", "status": "todo"},
                    ],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    phases = response.json()["phases"]

    # Complete the todo first
    todo_id = phases[0]["todos"][0]["id"]
    response = client.patch(
        f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers
    )
    assert response.status_code == 200

    # Mark task as done (all todos are done)
    response = client.patch(f"/tasks/{task_id}?status=done", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "done"
    assert data["progress_percent"] == 100
    assert data["phases"][0]["status"] == "completed"


def test_task_in_progress_does_not_cascade(client: TestClient, auth_headers: dict):
    """
    Test that marking a task as 'in_progress' does NOT cascade to phases/todos.
    Only 'done' should trigger the cascade.
    """
    # Create a task with todos in various states
    response = client.post(
        "/tasks/",
        json={
            "name": "In Progress Task",
            "priority": "medium",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "not_started",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1", "status": "todo"},
                    ],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Mark task as in_progress (should not cascade)
    response = client.patch(
        f"/tasks/{task_id}?status=in_progress", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "in_progress"
    # Phase and todo should remain unchanged
    assert data["phases"][0]["status"] == "not_started"
    assert data["phases"][0]["todos"][0]["status"] == "todo"


def test_task_done_idempotent(client: TestClient, auth_headers: dict):
    """
    Test that marking a task as 'done' multiple times is idempotent.
    """
    # Create a task
    response = client.post(
        "/tasks/",
        json={
            "name": "Idempotent Task",
            "priority": "low",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "not_started",
                    "order": 1,
                    "todos": [
                        {"name": "Todo 1", "status": "todo"},
                    ],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    phases = response.json()["phases"]

    # First complete the todo (required by validation)
    todo_id = phases[0]["todos"][0]["id"]
    response = client.patch(
        f"/todos/{todo_id}", json={"status": "done"}, headers=auth_headers
    )
    assert response.status_code == 200

    # Mark task as done first time
    response = client.patch(f"/tasks/{task_id}?status=done", headers=auth_headers)
    assert response.status_code == 200

    # Mark task as done second time (should be idempotent)
    response = client.patch(f"/tasks/{task_id}?status=done", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "done"
    assert data["progress_percent"] == 100
    assert data["phases"][0]["status"] == "completed"
    assert data["phases"][0]["todos"][0]["status"] == "done"
