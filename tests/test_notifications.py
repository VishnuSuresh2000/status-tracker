import os
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from notifications import (
    add_notification,
    get_unread_notifications,
    get_all_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    send_task_reminder,
    send_task_completion_notification,
    Notification,
    engine as notifications_engine,
)
import pytest
from fastapi.testclient import TestClient
from main import app, get_session


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

    # Override the notifications engine
    import notifications

    notifications.engine = engine

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
    """Return valid authentication headers for API calls."""
    token = os.getenv("API_AUTH_TOKEN", "secret-token-123")
    return {"Authorization": f"Bearer {token}"}


class TestAddNotification:
    def test_add_notification(self, session: Session):
        notification = add_notification(
            task_id=1,
            task_name="Test Task",
            message="Test message",
            notification_type="reminder",
        )

        assert notification.id is not None
        assert notification.task_id == 1
        assert notification.task_name == "Test Task"
        assert notification.message == "Test message"
        assert notification.notification_type == "reminder"
        assert notification.is_read == False

    def test_add_notification_verify_timestamp(self, session: Session):
        from datetime import datetime, timezone

        notification = add_notification(
            task_id=1,
            task_name="Test Task",
            message="Test message",
        )

        assert notification.created_at is not None
        assert isinstance(notification.created_at, datetime)
        # Check that it's a recent timestamp (within last minute)
        now = datetime.now(timezone.utc)
        # Ensure both datetimes are timezone-aware for comparison
        if notification.created_at.tzinfo is None:
            notification.created_at = notification.created_at.replace(
                tzinfo=timezone.utc
            )
        assert (now - notification.created_at).total_seconds() < 60


class TestGetUnreadNotifications:
    def test_get_unread_notifications(self, session: Session):
        # Create notifications
        notif1 = add_notification(1, "Task 1", "Message 1", "reminder")
        notif2 = add_notification(2, "Task 2", "Message 2", "reminder")
        notif3 = add_notification(3, "Task 3", "Message 3", "reminder")

        # Mark one as read
        mark_notification_as_read(notif2.id, session)

        # Get unread
        unread = get_unread_notifications(session)

        assert len(unread) == 2
        assert all(not n.is_read for n in unread)
        assert notif1.id in [n.id for n in unread]
        assert notif3.id in [n.id for n in unread]
        assert notif2.id not in [n.id for n in unread]

    def test_get_unread_notifications_ordering(self, session: Session):
        import time

        notif1 = add_notification(1, "Task 1", "Message 1", "reminder")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        notif2 = add_notification(2, "Task 2", "Message 2", "reminder")
        time.sleep(0.01)
        notif3 = add_notification(3, "Task 3", "Message 3", "reminder")

        unread = get_unread_notifications(session)

        # Should be ordered newest first
        assert unread[0].id == notif3.id
        assert unread[1].id == notif2.id
        assert unread[2].id == notif1.id


class TestGetAllNotifications:
    def test_get_all_notifications(self, session: Session):
        # Create multiple notifications
        for i in range(60):
            add_notification(i, f"Task {i}", f"Message {i}", "reminder")

        all_notifications = get_all_notifications(session)

        # Should respect default limit of 50
        assert len(all_notifications) == 50

    def test_get_all_notifications_ordering(self, session: Session):
        import time

        notif1 = add_notification(1, "Task 1", "Message 1", "reminder")
        time.sleep(0.01)
        notif2 = add_notification(2, "Task 2", "Message 2", "reminder")
        time.sleep(0.01)
        notif3 = add_notification(3, "Task 3", "Message 3", "reminder")

        # Mark one as read to verify ordering includes read notifications
        mark_notification_as_read(notif2.id, session)

        all_notifications = get_all_notifications(session)

        # Should be ordered newest first, regardless of read status
        assert all_notifications[0].id == notif3.id
        assert all_notifications[1].id == notif2.id
        assert all_notifications[2].id == notif1.id


class TestMarkNotificationAsRead:
    def test_mark_notification_as_read(self, session: Session):
        notification = add_notification(1, "Task 1", "Message 1", "reminder")
        assert notification.is_read == False

        result = mark_notification_as_read(notification.id, session)

        assert result == True

        # Verify in database
        from sqlmodel import select

        stmt = select(Notification).where(Notification.id == notification.id)
        updated = session.exec(stmt).first()
        assert updated.is_read == True

    def test_mark_notification_as_read_nonexistent(self, session: Session):
        result = mark_notification_as_read(999, session)
        assert result == False


class TestMarkAllNotificationsAsRead:
    def test_mark_all_notifications_as_read(self, session: Session):
        # Create multiple unread notifications
        add_notification(1, "Task 1", "Message 1", "reminder")
        add_notification(2, "Task 2", "Message 2", "reminder")
        add_notification(3, "Task 3", "Message 3", "reminder")

        count = mark_all_notifications_as_read(session)

        assert count == 3

        # Verify all are marked as read
        unread = get_unread_notifications(session)
        assert len(unread) == 0


class TestUtilityFunctions:
    def test_send_task_reminder(self, session: Session):
        notification = send_task_reminder(42, "Important Task")

        assert notification.task_id == 42
        assert notification.task_name == "Important Task"
        assert "Important Task" in notification.message
        assert "42" in notification.message
        assert "still in progress" in notification.message
        assert notification.notification_type == "reminder"
        assert notification.is_read == False

    def test_send_task_completion_notification(self, session: Session):
        notification = send_task_completion_notification(99, "Completed Task")

        assert notification.task_id == 99
        assert notification.task_name == "Completed Task"
        assert "Completed Task" in notification.message
        assert "completed" in notification.message
        assert notification.notification_type == "completion"
        assert notification.is_read == False


class TestNotificationAPIEndpoints:
    """API tests for single-notification acknowledgment feature."""

    def test_mark_single_notification_as_read(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Verify PATCH /notifications/{id}/read works correctly."""
        # Create a task first
        response = client.post(
            "/tasks/", json={"name": "API Test Task"}, headers=auth_headers
        )
        assert response.status_code == 200
        task_id = response.json()["id"]

        # Create a notification
        notification = Notification(
            task_id=task_id,
            task_name="API Test Task",
            message="Test notification message",
            notification_type="reminder",
            is_read=False,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        # Mark the notification as read via API
        response = client.patch(
            f"/notifications/{notification.id}/read", headers=auth_headers
        )
        data = response.json()

        # Verify response
        assert response.status_code == 200
        assert data["message"] == "Notification marked as read"
        assert data["notification_id"] == notification.id

    def test_mark_nonexistent_notification_returns_404(
        self, client: TestClient, auth_headers: dict
    ):
        """Verify that marking a non-existent notification returns 404."""
        response = client.patch("/notifications/999/read", headers=auth_headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "Notification not found"

    def test_mark_as_read_updates_is_read_field(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Verify that marking as read actually updates the is_read field in database."""
        # Create a task
        response = client.post(
            "/tasks/", json={"name": "DB Test Task"}, headers=auth_headers
        )
        assert response.status_code == 200
        task_id = response.json()["id"]

        # Create a notification
        notification = Notification(
            task_id=task_id,
            task_name="DB Test Task",
            message="Database verification test",
            notification_type="reminder",
            is_read=False,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        # Verify initial state
        assert notification.is_read == False

        # Mark as read via API
        response = client.patch(
            f"/notifications/{notification.id}/read", headers=auth_headers
        )
        assert response.status_code == 200

        # Verify in database
        from sqlmodel import select

        stmt = select(Notification).where(Notification.id == notification.id)
        updated_notification = session.exec(stmt).first()
        assert updated_notification.is_read == True
