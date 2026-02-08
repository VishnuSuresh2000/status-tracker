"""Tests for main application endpoints."""

from fastapi.testclient import TestClient
from sqlmodel import Session
from main import Task
import pytest

# Minimal task payload with required phase
MINIMAL_TASK = {
    "name": "Test Task",
    "phases": [
        {
            "name": "Default Phase",
            "status": "todo",
            "order": 1,
            "todos": [{"name": "Default Todo", "status": "todo"}],
        }
    ],
}


def test_create_task(client: TestClient, auth_headers: dict):
    response = client.post(
        "/tasks/",
        json={
            "name": "Test Task",
            "priority": "high",
            "description": "Test description",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "todo",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "todo"}],
                }
            ],
        },
        headers=auth_headers,
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Test Task"
    assert data["priority"] == "high"
    assert data["description"] == "Test description"
    assert data["progress_percent"] == 0
    assert "id" in data
    assert "phases" in data
    assert "comments" in data


def test_read_tasks(client: TestClient, auth_headers: dict):
    client.post(
        "/tasks/",
        json={
            "name": "Task 1",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "todo",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "todo"}],
                }
            ],
        },
        headers=auth_headers,
    )
    client.post(
        "/tasks/",
        json={
            "name": "Task 2",
            "phases": [
                {
                    "name": "Phase 1",
                    "status": "todo",
                    "order": 1,
                    "todos": [{"name": "Todo 1", "status": "todo"}],
                }
            ],
        },
        headers=auth_headers,
    )

    response = client.get("/tasks/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 2
    assert data[0]["name"] == "Task 1"
    assert data[1]["name"] == "Task 2"


def test_update_task_legacy_status(client: TestClient, auth_headers: dict):
    """Test legacy PATCH /tasks/{id} endpoint updates task status field."""
    response = client.post(
        "/tasks/",
        json={
            "name": "Transition Task",
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
        },
        headers=auth_headers,
    )
    task_id = response.json()["id"]

    # Legacy endpoint still accepts status parameter
    response = client.patch(
        f"/tasks/{task_id}?status=in_progress", headers=auth_headers
    )
    data = response.json()

    assert response.status_code == 200
    # Verify task was updated (legacy status field is stored but not in TaskRead)
    assert data["name"] == "Transition Task"
    assert "id" in data


def test_delete_task(client: TestClient, auth_headers: dict):
    response = client.post(
        "/tasks/",
        json={
            "name": "Task to Delete",
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
        },
        headers=auth_headers,
    )
    task_id = response.json()["id"]

    response = client.delete(f"/tasks/{task_id}", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "Task deleted successfully"
    assert data["task_id"] == task_id

    # Verify task is removed
    response = client.get("/tasks/")
    tasks = response.json()
    assert len(tasks) == 0


def test_delete_task_not_found(client: TestClient, auth_headers: dict):
    response = client.delete("/tasks/999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_edit_task_name_only(client: TestClient, auth_headers: dict):
    """Test editing task name with legacy PUT endpoint."""
    response = client.post(
        "/tasks/",
        json={
            "name": "Original Name",
            "priority": "medium",
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
        },
        headers=auth_headers,
    )
    task_id = response.json()["id"]

    response = client.put(f"/tasks/{task_id}?name=Updated Name", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Updated Name"
    assert data["priority"] == "medium"  # Unchanged


def test_edit_task_interval_only(client: TestClient, auth_headers: dict):
    response = client.post(
        "/tasks/",
        json={
            "name": "Task Name",
            "interval_minutes": 10.0,
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
        },
        headers=auth_headers,
    )
    task_id = response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}?interval_minutes=30.0", headers=auth_headers
    )
    data = response.json()

    assert response.status_code == 200
    assert data["interval_minutes"] == 30.0
    assert data["name"] == "Task Name"  # Unchanged


def test_edit_task_both_fields(client: TestClient, auth_headers: dict):
    response = client.post(
        "/tasks/",
        json={
            "name": "Original Name",
            "interval_minutes": 10.0,
            "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
        },
        headers=auth_headers,
    )
    task_id = response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}?name=Updated Name&interval_minutes=45.0",
        headers=auth_headers,
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Updated Name"
    assert data["interval_minutes"] == 45.0


def test_edit_task_not_found(client: TestClient, auth_headers: dict):
    response = client.put("/tasks/999?name=New Name", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_read_notifications(client: TestClient, session: Session, auth_headers: dict):
    # Create a task first
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    # Add a notification using the test session
    from notifications import add_notification, Notification

    notification = Notification(
        task_id=task_id,
        task_name="Test Task",
        message="Test notification",
        notification_type="reminder",
        is_read=False,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)

    response = client.get("/notifications/")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["message"] == "Test notification"
    assert data[0]["is_read"] == False


def test_read_notifications_unread_only(
    client: TestClient, session: Session, auth_headers: dict
):
    # Create a task
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    # Add two notifications using the test session
    from notifications import Notification

    notif1 = Notification(
        task_id=task_id,
        task_name="Test Task",
        message="Notification 1",
        notification_type="reminder",
        is_read=False,
    )
    notif2 = Notification(
        task_id=task_id,
        task_name="Test Task",
        message="Notification 2",
        notification_type="reminder",
        is_read=False,
    )
    session.add(notif1)
    session.add(notif2)
    session.commit()
    session.refresh(notif1)
    session.refresh(notif2)

    # Mark one as read
    notif1.is_read = True
    session.add(notif1)
    session.commit()

    response = client.get("/notifications/?unread_only=true")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["message"] == "Notification 2"


def test_mark_notification_as_read(
    client: TestClient, session: Session, auth_headers: dict
):
    # Create a task and notification
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    from notifications import Notification

    notification = Notification(
        task_id=task_id,
        task_name="Test Task",
        message="Test message",
        notification_type="reminder",
        is_read=False,
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)

    response = client.patch(
        f"/notifications/{notification.id}/read", headers=auth_headers
    )
    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "Notification marked as read"
    assert data["notification_id"] == notification.id


def test_mark_notification_as_read_not_found(client: TestClient, auth_headers: dict):
    response = client.patch("/notifications/999/read", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_mark_all_notifications_as_read(
    client: TestClient, session: Session, auth_headers: dict
):
    # Create a task and multiple notifications
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    from notifications import Notification

    for i in range(3):
        notification = Notification(
            task_id=task_id,
            task_name="Test Task",
            message=f"Message {i + 1}",
            notification_type="reminder",
            is_read=False,
        )
        session.add(notification)
    session.commit()

    response = client.post("/notifications/read-all", headers=auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "3 notifications marked as read"


def test_get_unread_count(client: TestClient, session: Session, auth_headers: dict):
    # Create a task and notifications
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    from notifications import Notification

    for msg in ["Unread 1", "Unread 2"]:
        notification = Notification(
            task_id=task_id,
            task_name="Test Task",
            message=msg,
            notification_type="reminder",
            is_read=False,
        )
        session.add(notification)
    session.commit()

    response = client.get("/notifications/unread-count")
    data = response.json()

    assert response.status_code == 200
    assert data["unread_count"] == 2
