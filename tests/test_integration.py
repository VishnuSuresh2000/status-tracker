import os
import pytest
from fastapi.testclient import TestClient
from main import app, get_session, Task
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from datetime import datetime, timezone, timedelta
from worker import check_and_notify_tasks
from unittest.mock import patch


# Setup in-memory database for integration tests
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
def auth_headers_fixture():
    """Return valid authentication headers for POST /tasks/."""
    token = os.getenv("API_AUTH_TOKEN", "secret-token-123")
    return {"Authorization": f"Bearer {token}"}


def test_full_task_notification_lifecycle(
    client: TestClient, session: Session, auth_headers: dict
):
    # 1. Create a task
    response = client.post(
        "/tasks/",
        json={"name": "Integration Test Task", "interval_minutes": 1.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    task_data = response.json()
    task_id = task_data["id"]

    # 2. Move to in_progress
    response = client.patch(f"/tasks/{task_id}", params={"status": "in_progress"}, headers=auth_headers)
    assert response.status_code == 200
    # assert response.json()["status"] == "in_progress"  # status removed from TaskRead

    # 3. Manually set last_ping to the past to trigger notification
    task = session.get(Task, task_id)
    task.last_ping = datetime.now(timezone.utc) - timedelta(minutes=2)
    session.add(task)
    session.commit()

    # 4. Run worker check (mocking the engine in worker.py and notifications.py)
    with (
        patch("worker.engine", session.get_bind()),
        patch("notifications.engine", session.get_bind()),
    ):
        check_and_notify_tasks()

    # 5. Verify notification was created
    response = client.get("/notifications/")
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) > 0
    assert notifications[0]["task_id"] == task_id
    assert "Integration Test Task" in notifications[0]["message"]

    # 6. Mark as read
    notif_id = notifications[0]["id"]
    response = client.patch(f"/notifications/{notif_id}/read", headers=auth_headers)
    assert response.status_code == 200

    # 7. Check unread count
    response = client.get("/notifications/unread-count")
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0
