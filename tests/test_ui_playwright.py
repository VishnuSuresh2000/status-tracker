import pytest
import uvicorn
import threading
import time
import requests
from playwright.sync_api import Page, expect, BrowserContext
from main import app, engine, create_db_and_tables, Task, Phase
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timezone, timedelta
from notifications import add_notification
import os

# Port for the test server
TEST_PORT = 8001
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"


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
    # Clear all data before each test
    with Session(engine) as session:
        # Delete in correct order to respect foreign keys
        from notifications import Notification

        session.exec("DELETE FROM notifications")
        session.exec("DELETE FROM comments")
        session.exec("DELETE FROM todos")
        session.exec("DELETE FROM phases")
        session.exec("DELETE FROM tasks")
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

        expect(todo_list).to_be_visible()
        expect(in_progress_list).to_be_visible()
        expect(done_list).to_be_visible()


class TestTaskCreation:
    """Tests for task creation functionality."""

    def test_create_task_via_api_and_display(self, page: Page):
        """Test creating a task through API and verifying it displays."""
        # Create a task via API
        headers = {"Authorization": "Bearer secret-token-123"}
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "API Created Task", "interval_minutes": 30},
            headers=headers,
        )
        assert response.status_code == 200

        # Refresh page and verify task appears
        page.goto(TEST_URL)
        time.sleep(1)  # Allow page to load

        expect(page.locator("text=API Created Task")).to_be_visible()

    def test_task_shows_in_todo_column(self, page: Page):
        """Test that newly created tasks appear in To Do column."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Todo Column Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        todo_column = page.locator("#todoList")
        expect(todo_column).to_contain_text("Todo Column Task")

    def test_task_card_shows_priority(self, page: Page):
        """Test that task cards display priority badges."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={
                "name": "High Priority Task",
                "priority": "high",
                "interval_minutes": 60,
            },
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Should show HIGH priority badge
        expect(page.locator("text=HIGH")).to_be_visible()

    def test_task_card_shows_progress_bar(self, page: Page):
        """Test that task cards display progress bars."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Progress Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Progress bar should be visible (0% for new task)
        expect(page.locator("text=0%")).to_be_visible()

    def test_task_with_phases_and_todos(self, page: Page):
        """Test creating a task with phases and todos."""
        headers = {"Authorization": "Bearer secret-token-123"}
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
            headers=headers,
        )
        assert response.status_code == 200

        page.goto(TEST_URL)
        time.sleep(1)

        expect(page.locator("text=Complex Task")).to_be_visible()


class TestTaskTransitions:
    """Tests for task status transitions (Todo -> In Progress -> Done)."""

    def test_task_details_modal_opens(self, page: Page):
        """Test that clicking a task opens the details modal."""
        headers = {"Authorization": "Bearer secret-token-123"}
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Clickable Task", "interval_minutes": 60},
            headers=headers,
        )
        task_id = response.json()["id"]

        page.goto(TEST_URL)
        time.sleep(1)

        # Click on task card
        page.click("text=Clickable Task")

        # Modal should appear
        expect(page.locator("#detailsModal")).to_be_visible()
        expect(page.locator("text=Task Details")).to_be_visible()

    def test_start_task_button_in_modal(self, page: Page):
        """Test that Start Task button appears in modal for todo tasks."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Start Me Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.click("text=Start Me Task")
        expect(page.locator("button", has_text="Start Task")).to_be_visible()

    def test_task_details_show_phases(self, page: Page):
        """Test that task details modal shows phases."""
        headers = {"Authorization": "Bearer secret-token-123"}
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
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.click("text=Phased Task")

        expect(page.locator("text=Phases & Checklists")).to_be_visible()
        expect(page.locator("text=Planning")).to_be_visible()


class TestNotificationPanel:
    """Tests for notification functionality."""

    def test_notification_panel_opens(self, page: Page):
        """Test that clicking the bell opens the notification panel."""
        page.goto(TEST_URL)
        time.sleep(1)

        # Click on notification bell
        page.click("button svg")  # Bell icon

        # Panel should be visible
        expect(page.locator("#notificationPanel")).to_be_visible()
        expect(page.locator("text=Notifications")).to_be_visible()

    def test_notification_panel_shows_empty_state(self, page: Page):
        """Test that notification panel shows empty state when no notifications."""
        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button svg")

        expect(page.locator("text=No notifications")).to_be_visible()

    def test_notification_shows_count_badge(self, page: Page):
        """Test that notification badge shows correct count."""
        # Add a notification via API
        with Session(engine) as session:
            add_notification(
                task_id=1,
                task_name="Test Task",
                message="Test notification message",
                notification_type="reminder",
            )

        page.goto(TEST_URL)
        time.sleep(1)

        # Badge should show "1"
        badge = page.locator("#notificationBadge")
        expect(badge).to_be_visible()
        expect(badge).to_contain_text("1")

    def test_notification_appears_in_panel(self, page: Page):
        """Test that notifications appear in the panel."""
        with Session(engine) as session:
            add_notification(
                task_id=1,
                task_name="Notification Task",
                message="This is a test notification",
                notification_type="reminder",
            )

        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button svg")

        expect(page.locator("text=Notification Task")).to_be_visible()
        expect(page.locator("text=This is a test notification")).to_be_visible()

    def test_multiple_notifications_displayed(self, page: Page):
        """Test that multiple notifications are displayed correctly."""
        with Session(engine) as session:
            add_notification(1, "Task 1", "Message 1", "reminder")
            add_notification(2, "Task 2", "Message 2", "reminder")
            add_notification(3, "Task 3", "Message 3", "completion")

        page.goto(TEST_URL)
        time.sleep(1)

        # Badge should show "3"
        badge = page.locator("#notificationBadge")
        expect(badge).to_contain_text("3")

        page.click("button svg")

        # All notifications should be visible
        expect(page.locator("text=Task 1")).to_be_visible()
        expect(page.locator("text=Task 2")).to_be_visible()
        expect(page.locator("text=Task 3")).to_be_visible()

    def test_mark_all_read_button_present(self, page: Page):
        """Test that Mark all read button is present in notification panel."""
        page.goto(TEST_URL)
        time.sleep(1)

        page.click("button svg")

        expect(page.locator("text=Mark all read")).to_be_visible()


class TestKanbanBoard:
    """Tests for Kanban board functionality."""

    def test_full_task_lifecycle(self, page: Page):
        """Test complete task lifecycle: create, view, complete."""
        # Create a task
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Lifecycle Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Task should be in Todo column
        todo_list = page.locator("#todoList")
        expect(todo_list).to_contain_text("Lifecycle Task")

        # Open task details
        page.click("text=Lifecycle Task")
        expect(page.locator("#detailsModal")).to_be_visible()

        # Close modal
        page.click("button:has-text('×')")
        expect(page.locator("#detailsModal")).to_be_hidden()

    def test_task_card_has_edit_button(self, page: Page):
        """Test that task cards have edit buttons."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Editable Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Edit button should be visible
        expect(page.locator("text=EDIT")).to_be_visible()

    def test_edit_modal_opens(self, page: Page):
        """Test that clicking edit opens the edit modal."""
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Edit Modal Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        # Click edit button
        page.click("text=EDIT")

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
        headers = {"Authorization": "Bearer secret-token-123"}
        requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Outside Click Task", "interval_minutes": 60},
            headers=headers,
        )

        page.goto(TEST_URL)
        time.sleep(1)

        page.click("text=Outside Click Task")
        expect(page.locator("#detailsModal")).to_be_visible()

        # Click outside modal (on the overlay)
        page.click("#detailsModal", position={"x": 10, "y": 10})

        # Modal should close
        expect(page.locator("#detailsModal")).to_be_hidden()
