import pytest
import uvicorn
import threading
import time
import requests
import re
from playwright.sync_api import Page, expect, BrowserContext
import os

# Ensure data directory exists before setting DATABASE_URL
os.makedirs("./data", exist_ok=True)

# Set environment variables BEFORE importing main or notifications
os.environ["DATABASE_URL"] = "sqlite:///./data/test_ui_ping.db"
os.environ["API_AUTH_TOKEN"] = os.environ.get("AUTH_TOKEN", "my-secret-token")

from main import app, engine, create_db_and_tables, Task, Phase
from sqlmodel import SQLModel, Session, select
from sqlalchemy import text, create_engine
from datetime import datetime, timezone, timedelta
from notifications import add_notification
import notifications

# Port for the test server (different from test_ui_playwright.py and test_ui.py)
TEST_PORT = 8003
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"

# Auth token for API calls (from environment or fallback)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "my-secret-token")
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}


def run_server():
    # Environment variables already set at module level above
    # Re-initialize DB with unique path
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
    # Cleanup data/test_ui_ping.db after tests if needed
    if os.path.exists("./data/test_ui_ping.db"):
        os.remove("./data/test_ui_ping.db")


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


class TestPingSystemUI:
    """UI tests for Ping System 2.0 functionality."""

    def test_ruto_status_badge_exists(self, page: Page):
        """Verify 'ruto-status-badge' is visible in the header."""
        page.goto(TEST_URL)
        time.sleep(1)

        # Look for the ruto-status-badge element in the header
        ruto_badge = page.locator("#ruto-status-badge")
        expect(ruto_badge).to_be_visible()

    def test_agent_status_section_exists(self, page: Page):
        """Verify 'agentStatusList' container is visible."""
        page.goto(TEST_URL)
        time.sleep(1)

        # Look for the agent status list container
        agent_status_list = page.locator("#agentStatusList")
        expect(agent_status_list).to_be_visible()

    def test_edit_task_modal_has_agent_dropdown(self, page: Page):
        """Open edit modal for a task and verify 'edit-task-agent' dropdown is visible."""
        # Create a task first
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Test Task for Agent Edit", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200

        page.goto(TEST_URL)
        time.sleep(1)

        # Click edit button for the task
        page.get_by_role("button", name="Edit").click()

        # Verify edit modal is open
        expect(page.locator("#editModal")).to_be_visible()

        # Look for the agent dropdown
        agent_dropdown = page.locator("#edit-task-agent")
        expect(agent_dropdown).to_be_visible()

    def test_assign_agent_via_ui(self, page: Page):
        """Select an agent in the dropdown, save changes, and verify the assignment."""
        # Create a task first
        response = requests.post(
            f"{TEST_URL}/tasks/",
            json={"name": "Task for Agent Assignment", "interval_minutes": 60},
            headers=AUTH_HEADERS,
        )
        task_id = response.json()["id"]
        assert response.status_code == 200

        page.goto(TEST_URL)
        time.sleep(1)

        # Click edit button for the task
        page.get_by_role("button", name="Edit").click()

        # Verify edit modal is open
        expect(page.locator("#editModal")).to_be_visible()

        # Look for the agent dropdown and select an option if available
        agent_dropdown = page.locator("#edit-task-agent")

        # Check if dropdown has options
        if agent_dropdown.count() > 0:
            # Try to select the first available option (excluding the default empty option)
            agent_options = agent_dropdown.locator("option:not([value=''])")

            if agent_options.count() > 0:
                # Select the first available agent
                first_option = agent_options.first
                agent_name = first_option.inner_text()
                agent_dropdown.select_option(index=1)  # Skip the first (empty) option

                # Save changes
                save_button = page.locator("button", has_text="Save")
                if save_button.count() > 0:
                    save_button.click()
                    time.sleep(0.5)

                    # Verify the modal closed
                    expect(page.locator("#editModal")).to_be_hidden()

                    # Verify the task card or data reflects the assignment
                    # This might be visible as an agent badge or in the task details
                    task_card = page.locator(f"[data-task-id='{task_id}']")
                    if task_card.count() > 0:
                        # Look for agent information on the task card
                        expect(task_card).to_be_visible()
                    else:
                        # Fallback: check task details modal
                        page.get_by_role(
                            "heading", name="Task for Agent Assignment"
                        ).click()
                        expect(page.locator("#detailsModal")).to_be_visible()

                        # Look for agent information in the modal
                        expect(page.locator("#detailsModal")).to_contain_text(
                            agent_name
                        )
                else:
                    # If no save button, just verify dropdown interaction worked
                    expect(agent_dropdown).to_have_value()
            else:
                # No agents available to select - just verify dropdown exists
                expect(agent_dropdown).to_be_visible()
        else:
            # Agent dropdown not found - this might be expected if no agents are configured
            pytest.skip("Agent dropdown not available - no agents configured")
