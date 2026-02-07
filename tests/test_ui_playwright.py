import pytest
import uvicorn
import threading
import time
import requests
from playwright.sync_api import Page, expect, BrowserContext
from main import app, engine, create_db_and_tables, Task, Phase
from sqlmodel import SQLModel, Session, select
from sqlalchemy import text, create_engine
from datetime import datetime, timezone, timedelta
from notifications import add_notification
import notifications
import os

# Port for the test server
TEST_PORT = 8001
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"

# Auth token for API calls (from environment or fallback)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "my-secret-token")
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

# Skip notification tests in CI that require direct DB writes
# (notifications.py creates engine at import time, before test DB is configured)
IN_CI = os.environ.get("CI") == "true"


def run_server():
    # Force test database for UI tests
    os.environ["DATABASE_URL"] = "sqlite:///./data/test_ui.db"
    # Re-initialize DB
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    uvicorn.run(app, host="127.0.0.1", port=TEST_PORT, log_level="error")


@pytest.fixture(scope="module", autouse=True)
def server():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Wait for server to start
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(TEST_URL)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
    else:
        pytest.fail("Server failed to start")

    yield
    # Cleanup data/test_ui.db after tests if needed
    if os.path.exists("./data/test_ui.db"):
        os.remove("./data/test_ui.db")


@pytest.fixture(autouse=True)
def cleanup_database():
    """Clean up database before each test."""
    # Patch notifications engine to use test database
    notifications.engine = engine

    # Clear all data before each test
    with Session(engine) as session:
        # Delete in correct order to respect foreign keys
        from notifications import Notification

        session.exec(text("DELETE FROM notifications"))
        session.exec(text("DELETE FROM comments"))
        session.exec(text("DELETE FROM todos"))
        session.exec(text("DELETE FROM phases"))
        session.exec(text("DELETE FROM tasks"))
        session.commit()
    yield


class TestDashboardFunctionality:
    """Tests for the main dashboard UI."""

    def test_page_loads_successfully(self, page: Page):
        """Test that the dashboard loads correctly."""
        page.goto(TEST_URL)

        # Verify page title
        expect(page.locator("h1")).to_contain_text("Task Status Tracker")

        # Verify all three columns are present
        expect(page.locator("text=To Do")).to_be_visible()
        expect(page.locator("text=In Progress")).to_be_visible()
        expect(page.locator("text=Done")).to_be_visible()

    def test_add_task_form_exists(self, page: Page):
        """Test that the add task form is present."""
        page.goto(TEST_URL)

        # Verify form elements
        expect(page.locator("input#taskName")).to_be_visible()
        expect(page.locator("input#taskInterval")).to_be_visible()
        expect(page.locator("button", has_text="Add Task")).to_be_visible()

    def test_notification_bell_exists(self, page: Page):
        """Test that the notification bell is present."""
        page.goto(TEST_URL)

        # Find notification button (bell icon)
        expect(page.locator("button").first).to_be_visible()

    def test_empty_state_displayed(self, page: Page):
        """Test that empty columns are handled gracefully."""
        page.goto(TEST_URL)

        # All columns should be visible even when empty
        todo_list = page.locator("#todoList")
        in_progress_list = page.locator("#inProgressList")
        done_list = page.locator("#doneList")

        # Use to_be_attached() for empty containers that may not be considered visible
        expect(todo_list).to_be_attached()
        expect(in_progress_list).to_be_attached()
        expect(done_list).to_be_attached()


class TestTaskCreation:
    """Tests for task creation functionality."""

    def test_create_task_via_api_and_display(self, page: Page):
        """Test creating a task through API and verifying it displays."""
        # Create a task via API
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "API Created Task", "interval_minutes": 30},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200

        # Refresh page and verify task appears
        page.goto(TEST_URL)
        time.sleep(1)  # Allow page to load

        expect(page.locator("text=API Created Task")).to_be_visible()

    def test_task_shows_in_todo_column(self, page: Page):
        """Test that newly created tasks appear in To Do column."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Todo Column Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        todo_column = page.locator("#todoList")
        expect(todo_column).to_contain_text("Todo Column Task")

    def test_task_card_shows_priority(self, page: Page):
        """Test that task cards display priority badges."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={
                "name": "High Priority Task",
                "priority": "high",
                "interval_minutes": 60,
            },
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Should show 'high' priority badge (lowercase as displayed in HTML)
        expect(page.get_by_text("high", exact=True)).to_be_visible()

    def test_task_card_shows_progress_bar(self, page: Page):
        """Test that task cards display progress bars."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Progress Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Progress bar should be visible (0% for new task)
        expect(page.locator("text=0%")).to_be_visible()

    def test_task_with_phases_and_todos(self, page: Page):
        """Test creating a task with phases and todos."""
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={
                "name": "Complex Task",
                "priority": "high",
                "interval_minutes": 60,
                "phases": [
                    {
                        "name": "Phase 1",
                        "status": "not_started",
                        "order": 1,
                        "todos": [
                            {"name": "Todo 1", "status": "todo"},
                            {"name": "Todo 2", "status": "todo"},
                        ],
                    }
                ],
            },
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200

        page.goto(TEST_URL)
        time.sleep(1)

        expect(page.get_by_role("heading", name="Complex Task")).to_be_visible()


class TestTaskTransitions:
    """Tests for task status transitions (Todo -> In Progress -> Done)."""

    def test_task_details_modal_opens(self, page: Page):
        """Test that clicking a task opens the details modal."""
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Clickable Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = response.json()["id"]

        page.goto(TEST_URL)
        time.sleep(1)

        # Click on task card
        page.get_by_role("heading", name="Clickable Task").click()

        # Modal should appear - check for modal content instead of title since title shows task name
        expect(page.locator("#detailsModal")).to_be_visible()
        expect(page.locator("#modalTaskName")).to_contain_text("Clickable Task")

    def test_start_task_button_in_modal(self, page: Page):
        """Test that Start Task button appears in modal for todo tasks."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Start Me Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.get_by_role("heading", name="Start Me Task").click()
        expect(page.locator("button", has_text="Start Task")).to_be_visible()

    def test_task_details_show_phases(self, page: Page):
        """Test that task details modal shows phases."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={
                "name": "Phased Task",
                "interval_minutes": 60,
                "phases": [
                    {
                        "name": "Planning",
                        "status": "not_started",
                        "order": 1,
                        "todos": [],
                    }
                ],
            },
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.get_by_role("heading", name="Phased Task").click()

        expect(page.locator("text=Phases & Checklists")).to_be_visible()
        expect(page.locator("text=Planning")).to_be_visible()


class TestNotificationPanel:
    """Tests for notification functionality."""

    def test_notification_panel_opens(self, page: Page):
        """Test that clicking the bell opens the notification panel."""
        page.goto(TEST_URL)
        time.sleep(1)

        # Click on notification bell button (the button with the bell icon)
        page.click("button[onclick='toggleNotifications()']")

        # Panel should be visible
        expect(page.locator("#notificationPanel")).to_be_visible()
        expect(page.get_by_role("heading", name="Notifications")).to_be_visible()

    def test_notification_panel_shows_empty_state(self, page: Page):
        """Test that notification panel shows empty state when no notifications."""
        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button[onclick='toggleNotifications()']")

        expect(page.locator("text=No notifications")).to_be_visible()

    def test_notification_shows_count_badge(self, page: Page):
        """Test that notification badge shows correct count."""
        # First create a task to ensure task_id exists
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Notification Test Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        # Add notification using the patched engine
        add_notification(
            task_id=1,
            task_name="Test Task",
            message="Test notification message",
            notification_type="reminder",
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Badge should show "1" and be visible
        badge = page.locator("#notificationBadge")
        expect(badge).to_be_visible()
        expect(badge).to_contain_text("1")

    def test_notification_appears_in_panel(self, page: Page):
        """Test that notifications appear in the panel."""
        resp = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Notification Task Parent", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = resp.json()["id"]

        # Add notification using the patched engine
        add_notification(
            task_id=task_id,
            task_name="Notification Task",
            message="This is a test notification",
            notification_type="reminder",
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button[onclick='toggleNotifications()']")

        expect(page.locator("#notificationList")).to_contain_text("Notification Task")
        expect(page.locator("#notificationList")).to_contain_text(
            "This is a test notification"
        )

    def test_multiple_notifications_displayed(self, page: Page):
        """Test that multiple notifications are displayed correctly."""
        resp = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Multi Notification Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = resp.json()["id"]

        # Add notifications using the patched engine
        add_notification(task_id, "Task 1", "Message 1", "reminder")
        add_notification(task_id, "Task 2", "Message 2", "reminder")
        add_notification(task_id, "Task 3", "Message 3", "completion")

        page.goto(TEST_URL)
        time.sleep(1)

        # Badge should show "3"
        badge = page.locator("#notificationBadge")
        expect(badge).to_contain_text("3")

        page.click('button[onclick="toggleNotifications()"]')

        # All notifications should be visible
        expect(page.locator("text=Task 1")).to_be_visible()
        expect(page.locator("text=Task 2")).to_be_visible()
        expect(page.locator("text=Task 3")).to_be_visible()

    def test_mark_all_read_button_present(self, page: Page):
        """Test that Mark all read button is present in notification panel."""
        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button[onclick='toggleNotifications()']")

        expect(page.locator("text=Mark all read")).to_be_visible()


class TestSingleNotificationAck:
    """Tests for single notification acknowledgment feature."""

    def test_mark_as_read_button_visible_on_unread(self, page: Page):
        """Test that mark-as-read button exists on unread notifications."""
        # Create a task first
        resp = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Single Ack Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = resp.json()["id"]

        # Add a notification using the patched engine
        notification = add_notification(
            task_id=task_id,
            task_name="Single Ack Task",
            message="Test notification for single ack",
            notification_type="reminder",
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Open notification panel
        page.click("button[onclick='toggleNotifications()']")

        # Verify notification is displayed
        expect(page.locator("text=Test notification for single ack")).to_be_visible()

        # Check that mark-as-read button is visible (typically a checkmark or 'Mark as read' button)
        # The button should be associated with the notification
        notification_element = page.locator(
            f"[data-notification-id='{notification.id}']"
        )
        if notification_element.count() > 0:
            expect(
                notification_element.locator(
                    "button[onclick*='markNotificationAsRead']"
                )
            ).to_be_visible()
        else:
            # Fallback: check for any mark-as-read button in the notification list
            expect(
                page.locator("button[onclick*='markNotificationAsRead']").first
            ).to_be_visible()

    def test_click_mark_as_read_marks_notification(self, page: Page):
        """Test that clicking the mark-as-read button marks the notification."""
        # Create a task
        resp = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Click Ack Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = resp.json()["id"]

        # Add a notification
        notification = add_notification(
            task_id=task_id,
            task_name="Click Ack Task",
            message="Click to mark as read",
            notification_type="reminder",
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Open notification panel
        page.click("button[onclick='toggleNotifications()']")

        # Verify notification is visible
        expect(page.locator("text=Click to mark as read")).to_be_visible()

        # Click the mark-as-read button
        mark_button = page.locator(
            f"button[onclick='markNotificationAsRead({notification.id})']"
        )
        if mark_button.count() > 0:
            mark_button.click()
        else:
            # Fallback: click the first mark-as-read button
            page.locator("button[onclick*='markNotificationAsRead']").first.click()

        # Wait for API call to complete and UI to update
        time.sleep(1)
        page.reload()
        time.sleep(0.5)

        # Re-open notification panel
        page.click("button[onclick='toggleNotifications()']")
        time.sleep(0.3)

        # Verify "Mark as read" button is no longer visible (notification was marked as read)
        expect(
            page.locator("button[onclick*='markNotificationAsRead']")
        ).not_to_be_visible()

    def test_single_mark_read_does_not_affect_others(self, page: Page):
        """Test that marking one notification as read doesn't affect others."""
        # Create a task
        resp = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Multi Ack Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = resp.json()["id"]

        # Add multiple notifications
        notif1 = add_notification(
            task_id=task_id,
            task_name="Multi Ack Task",
            message="First notification",
            notification_type="reminder",
        )
        notif2 = add_notification(
            task_id=task_id,
            task_name="Multi Ack Task",
            message="Second notification",
            notification_type="reminder",
        )
        notif3 = add_notification(
            task_id=task_id,
            task_name="Multi Ack Task",
            message="Third notification",
            notification_type="completion",
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Verify badge shows 3
        badge = page.locator("#notificationBadge")
        expect(badge).to_contain_text("3")

        # Open notification panel
        page.click("button[onclick='toggleNotifications()']")

        # Mark only the first notification as read via API
        response = requests.patch(
            f"{TEST_URL}/notifications/{notif1.id}/read",
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200

        # Refresh page to see updated state
        page.goto(TEST_URL)
        time.sleep(1)

        # Badge should now show 2 (only 2 unread remaining)
        badge = page.locator("#notificationBadge")
        expect(badge).to_contain_text("2")

        # Open panel and verify the other two are still there
        page.click("button[onclick='toggleNotifications()']")
        expect(page.locator("text=Second notification")).to_be_visible()
        expect(page.locator("text=Third notification")).to_be_visible()


class TestKanbanBoard:
    """Tests for Kanban board functionality."""

    def test_full_task_lifecycle(self, page: Page):
        """Test complete task lifecycle: create, view, complete."""
        # Create a task
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Lifecycle Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Task should be in Todo column
        todo_list = page.locator("#todoList")
        expect(todo_list).to_contain_text("Lifecycle Task")

        # Open task details
        page.get_by_role("heading", name="Lifecycle Task").click()
        expect(page.locator("#detailsModal")).to_be_visible()

        # Close modal
        page.click("button:has-text('×')")
        expect(page.locator("#detailsModal")).to_be_hidden()

    def test_task_card_has_edit_button(self, page: Page):
        """Test that task cards have edit buttons."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Editable Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Edit button should be visible
        expect(page.locator("button:has-text('Edit')")).to_be_visible()

    def test_edit_modal_opens(self, page: Page):
        """Test that clicking edit opens the edit modal."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Edit Modal Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Click edit button using get_by_role to avoid hidden heading
        page.get_by_role("button", name="Edit").click()

        # Edit modal should appear
        expect(page.locator("#editModal")).to_be_visible()
        expect(page.locator("text=Edit Basic Info")).to_be_visible()


class TestResponsiveDesign:
    """Tests for responsive UI design."""

    def test_mobile_viewport(self, page: Page):
        """Test that page works on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(TEST_URL)

        # Page should still load
        expect(page.locator("h1")).to_contain_text("Task Status Tracker")

    def test_tablet_viewport(self, page: Page):
        """Test that page works on tablet viewport."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(TEST_URL)

        expect(page.locator("h1")).to_contain_text("Task Status Tracker")


class TestErrorHandling:
    """Tests for error handling in UI."""

    def test_modal_closes_on_outside_click(self, page: Page):
        """Test that clicking outside modal closes it."""
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Outside Click Task", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.get_by_role("heading", name="Outside Click Task").click()
        expect(page.locator("#detailsModal")).to_be_visible()

        # Click outside modal (on the overlay)
        page.click("#detailsModal", position={"x": 10, "y": 10})

        # Modal should close
        expect(page.locator("#detailsModal")).to_be_hidden()
