import pytest
import uvicorn
import threading
import time
import requests
from playwright.sync_api import Page, expect
from main import app, engine, create_db_and_tables
from sqlmodel import SQLModel, Session
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

def test_kanban_board_functionality(page: Page):
    page.goto(TEST_URL)
    
    # 1. Verify page title or heading
    expect(page.get_by_role("heading", name="Status Tracker")).to_be_visible()
    
    # 2. Add a new task
    task_name = "UI Test Task"
    page.get_by_placeholder("Enter task name...").fill(task_name)
    page.get_by_role("button", name="Add Task").click()
    
    # 3. Verify task appears in 'To Do' column
    todo_column = page.locator("#todo-list")
    expect(todo_column).to_contain_text(task_name)
    
    # 4. Move task to 'In Progress'
    task_item = page.get_by_text(task_name)
    # The 'Start' button moves it to in_progress
    page.locator(f"xpath=//div[contains(text(), '{task_name}')]/..//button[contains(text(), 'Start')]").click()
    
    # 5. Verify task moved to 'In Progress' column
    in_progress_column = page.locator("#in-progress-list")
    expect(in_progress_column).to_contain_text(task_name)
    
    # 6. Move task to 'Done'
    page.locator(f"xpath=//div[contains(text(), '{task_name}')]/..//button[contains(text(), 'Complete')]").click()
    
    # 7. Verify task moved to 'Done' column
    done_column = page.locator("#done-list")
    expect(done_column).to_contain_text(task_name)
    
    # 8. Delete the task
    page.locator(f"xpath=//div[contains(text(), '{task_name}')]/..//button[contains(text(), 'Delete')]").click()
    
    # 9. Verify task is gone
    expect(done_column).not_to_contain_text(task_name)

def test_notification_panel(page: Page):
    page.goto(TEST_URL)
    
    # Open notification panel
    page.get_by_role("button", name="🔔").click()
    
    # Verify panel is visible
    expect(page.get_by_text("Notifications")).to_be_visible()
    
    # Initially should be empty or show 'No notifications'
    # (Assuming the UI has such text)
    # expect(page.get_by_text("No notifications")).to_be_visible()
