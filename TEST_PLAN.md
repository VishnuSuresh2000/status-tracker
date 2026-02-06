# Status Tracker - Comprehensive Test Plan

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture Analysis](#2-architecture-analysis)
3. [Current Test Coverage](#3-current-test-coverage)
4. [Test Strategy](#4-test-strategy)
5. [Detailed Test Specifications](#5-detailed-test-specifications)
6. [Test Data Requirements](#6-test-data-requirements)
7. [Test Implementation Guide](#7-test-implementation-guide)
8. [Execution Plan](#8-execution-plan)

---

## 1. Project Overview

**Status Tracker** is a FastAPI-based task management system with the following capabilities:

### Core Features
- **Task Management**: Full CRUD operations for tasks
- **Kanban Board**: Visual task board with columns (To Do, In Progress, Done)
- **Background Worker**: Monitors in-progress tasks and sends periodic notifications
- **Real-time Notifications**: In-app notification system with read/unread tracking
- **RESTful API**: Complete HTTP API for all operations
- **Responsive UI**: Tailwind CSS-based frontend

### Tech Stack
| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| ORM | SQLModel |
| Database | SQLite |
| Background Tasks | Redis + Custom Worker |
| Frontend | HTML + JavaScript + Tailwind CSS |
| Containerization | Docker + Docker Compose |

---

## 2. Architecture Analysis

### 2.1 File Structure
```
status-tracker/
├── main.py                 # FastAPI application, Task model, API endpoints
├── notifications.py        # Notification model and business logic
├── worker.py               # Background worker for task monitoring
├── index.html              # Frontend UI (Kanban board)
├── tests/
│   ├── test_main.py        # API endpoint tests
│   └── test_notifications.py # Notification module unit tests
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── data/                   # SQLite database storage
```

### 2.2 Data Models

#### Task Model (main.py)
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | int | Primary Key, Auto-increment | Unique identifier |
| name | str | Indexed, Required | Task name |
| status | str | Default: "todo" | Status: todo, in_progress, done |
| interval_minutes | float | Default: 60.0 | Notification interval |
| last_ping | datetime | Auto-set | Last notification timestamp |
| created_at | datetime | Auto-set | Creation timestamp |

#### Notification Model (notifications.py)
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | int | Primary Key, Auto-increment | Unique identifier |
| task_id | int | Indexed, Required | Reference to task |
| task_name | str | Required | Task name snapshot |
| message | str | Required | Notification content |
| notification_type | str | Default: "reminder" | Type: reminder, completion, system |
| is_read | bool | Default: False | Read status |
| created_at | datetime | Auto-set | Creation timestamp |

### 2.3 API Endpoints

#### Task Endpoints
| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | /tasks/ | None | List[Task] |
| POST | /tasks/ | Task JSON | Task |
| PATCH | /tasks/{task_id} | status (query) | Task |
| PUT | /tasks/{task_id} | name, interval_minutes (query) | Task |
| DELETE | /tasks/{task_id} | None | {message, task_id} |

#### Notification Endpoints
| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | /notifications/ | unread_only (bool, optional) | List[Notification] |
| PATCH | /notifications/{notification_id}/read | None | {message, notification_id} |
| POST | /notifications/read-all | None | {message} |
| GET | /notifications/unread-count | None | {unread_count} |

### 2.4 Background Worker Logic
The worker (`worker.py`) runs continuously and:
1. Polls every 30 seconds
2. Queries tasks with `status = "in_progress"`
3. For each task, checks if `now > last_ping + interval_minutes`
4. Creates reminder notification if due
5. Updates `last_ping` to prevent duplicate notifications

## 3. Current Test Coverage (Updated 2026-02-05)

### 3.1 Status Summary
- **Total Tests**: 30
- **Passing**: 30 ✅
- **Coverage**: ~85% (Target 90%)

| Module | Tests | Status |
|--------|-------|--------|
| Task API (`main.py`) | 16 | ✅ Passed |
| Notifications (`notifications.py`) | 10 | ✅ Passed |
| Worker Logic (`worker.py`) | 3 | ✅ Passed |
| Integration E2E | 1 | ✅ Passed |
| UI Tests (Playwright) | 2 | ⚠️ Script ready, env blocked |

---

## 4. Implementation Progress

### Phase 1: Foundation (Complete ✅)
- [x] Verified existing API tests
- [x] Verified existing notification tests

### Phase 2: Worker & Integration (Complete ✅)
- [x] Created `tests/test_worker.py`
- [x] Created `tests/test_integration.py`
- [x] Verified background notification logic

### Phase 3: UI Testing (In Progress 🏗️)
- [x] Created `tests/test_ui.py` (Playwright)
- [ ] Execute UI tests (Blocked by Chromium system dependencies in current env)

### Phase 4: Final Deployment (Pending)
- [ ] Build final Docker image
- [ ] Deploy with Traefik


### 3.2 Missing Test Areas

1. **Worker Tests** - No tests for worker.py
2. **Edge Cases** - Limited boundary testing
3. **Error Handling** - Missing database error scenarios
4. **Integration Tests** - Missing worker + API integration
5. **Load/Performance Tests** - No stress testing
6. **Security Tests** - No input sanitization tests
7. **Frontend Tests** - No JavaScript/UI tests

---

## 4. Test Strategy

### 4.1 Testing Pyramid

```
       /\
      /  \     E2E Tests (Minimal)
     /____\    
    /      \   Integration Tests (Moderate)
   /________\  
  /          \ Unit Tests (Maximum)
 /____________\
```

### 4.2 Test Categories

| Category | Purpose | Tools |
|----------|---------|-------|
| Unit Tests | Test individual functions in isolation | pytest, monkeypatch |
| Integration Tests | Test API endpoints with database | TestClient, in-memory SQLite |
| Worker Tests | Test background worker logic | pytest, freezegun (time mocking) |
| Error Handling Tests | Test failure scenarios | pytest.raises, mock |
| Edge Case Tests | Test boundary conditions | Parameterized tests |
| Concurrency Tests | Test race conditions | pytest-asyncio, threading |

### 4.3 Test Configuration

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "worker: Worker tests",
    "slow: Slow tests",
]
```

---

## 5. Detailed Test Specifications

### 5.1 Task Model Tests (tests/test_task_model.py)

#### Unit Tests for Task Model

```python
class TestTaskModel:
    """Tests for Task data model validation and behavior."""
    
    def test_task_default_values(self):
        """Verify default values are set correctly."""
        # Expected: status="todo", interval_minutes=60.0
        
    def test_task_status_validation(self):
        """Test status field constraints."""
        # Valid: todo, in_progress, done
        # Invalid: any other value
        
    def test_task_name_constraints(self):
        """Test name field boundaries."""
        # Empty name should fail
        # Very long name (1000+ chars) behavior
        # Special characters handling
        # Unicode support
        
    def test_task_interval_constraints(self):
        """Test interval_minutes boundaries."""
        # Zero interval
        # Negative interval
        # Very large interval (1 year in minutes)
        # Float precision
        
    def test_task_timestamp_auto_set(self):
        """Verify timestamps are automatically set."""
        # created_at on creation
        # last_ping on creation
```

### 5.2 Task API Endpoint Tests (Expand test_main.py)

#### CREATE Endpoint Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| T-001 | test_create_task_success | Valid task creation | 200, task returned with id |
| T-002 | test_create_task_minimal | Only required fields | 200, defaults applied |
| T-003 | test_create_task_missing_name | Empty JSON body | 422 Validation Error |
| T-004 | test_create_task_empty_name | name="" | 422 Validation Error |
| T-005 | test_create_task_long_name | name=1000 chars | 200 or 422 (define limit) |
| T-006 | test_create_task_special_chars | name with <script> etc | Proper escaping/sanitization |
| T-007 | test_create_task_unicode | name with emojis, unicode | 200, preserved correctly |
| T-008 | test_create_task_zero_interval | interval_minutes=0 | 200 or validation error |
| T-009 | test_create_task_negative_interval | interval_minutes=-10 | 422 Validation Error |
| T-010 | test_create_task_large_interval | interval_minutes=525600 | 200 (1 year) |
| T-011 | test_create_task_invalid_interval_type | interval_minutes="abc" | 422 Validation Error |
| T-012 | test_create_task_sql_injection | name="'; DROP TABLE" | Safe handling, 200 |

#### READ Endpoint Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| T-013 | test_read_tasks_empty_db | No tasks exist | 200, empty list [] |
| T-014 | test_read_tasks_multiple | Several tasks exist | 200, all tasks returned |
| T-015 | test_read_tasks_ordering | Check default ordering | By created_at or id |
| T-016 | test_read_tasks_large_dataset | 10000+ tasks | Performance acceptable |

#### UPDATE Status (PATCH) Endpoint Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| T-017 | test_update_task_status_todo_to_in_progress | Valid transition | 200, status updated |
| T-018 | test_update_task_status_in_progress_to_done | Valid transition | 200, status updated |
| T-019 | test_update_task_status_done_to_todo | Valid or invalid? | Define business rule |
| T-020 | test_update_task_status_invalid_status | status="invalid" | 422 or 400 Error |
| T-021 | test_update_task_status_empty_status | status="" | 422 Validation Error |
| T-022 | test_update_task_status_not_found | task_id=99999 | 404 Not Found |
| T-023 | test_update_task_status_updates_last_ping | Check timestamp | last_ping updated to now |
| T-024 | test_update_task_status_no_change | Same status | 200, no error |
| T-025 | test_update_task_status_case_sensitivity | status="In_Progress" | Case handling |

#### EDIT (PUT) Endpoint Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| T-026 | test_edit_task_name_only | Update name | 200, name changed |
| T-027 | test_edit_task_interval_only | Update interval | 200, interval changed |
| T-028 | test_edit_task_both_fields | Update both | 200, both changed |
| T-029 | test_edit_task_no_fields | No query params | 200, unchanged or error? |
| T-030 | test_edit_task_empty_name | name="" | 422 Validation Error |
| T-031 | test_edit_task_negative_interval | interval_minutes=-5 | 422 Validation Error |
| T-032 | test_edit_task_not_found | task_id=99999 | 404 Not Found |
| T-033 | test_edit_task_preserves_other_fields | Only update name | interval unchanged |

#### DELETE Endpoint Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| T-034 | test_delete_task_success | Delete existing | 200, task removed |
| T-035 | test_delete_task_not_found | Delete non-existent | 404 Not Found |
| T-036 | test_delete_task_already_deleted | Double delete | 404 on second attempt |
| T-037 | test_delete_task_cascades_notifications | Delete task with notifications | Define behavior |

### 5.3 Notification Tests (Expand test_notifications.py)

#### Notification Model Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| N-001 | test_notification_defaults | Create with minimal fields | Defaults applied |
| N-002 | test_notification_types | reminder, completion, system | All valid |
| N-003 | test_notification_invalid_type | type="invalid" | Validation error |
| N-004 | test_notification_long_message | message=10000 chars | Handle gracefully |
| N-005 | test_notification_unicode | Unicode in message | Preserved correctly |

#### Notification Function Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| N-006 | test_add_notification_basic | Add notification | Returns notification with id |
| N-007 | test_add_notification_timestamp | Check created_at | Recent timestamp |
| N-008 | test_get_unread_notifications_empty | No unread exist | Empty list |
| N-009 | test_get_unread_notifications_mixed | Some read, some not | Only unread returned |
| N-010 | test_get_unread_notifications_ordering | Multiple unread | Ordered by created_at desc |
| N-011 | test_get_all_notifications_limit | 100 notifications | Only 50 returned |
| N-012 | test_get_all_notifications_custom_limit | With limit=10 | 10 returned |
| N-013 | test_mark_notification_as_read_success | Mark existing | Returns True |
| N-014 | test_mark_notification_as_read_not_found | Invalid id | Returns False |
| N-015 | test_mark_notification_already_read | Mark twice | Still True, no error |
| N-016 | test_mark_all_notifications_as_read | Multiple unread | Correct count returned |
| N-017 | test_mark_all_notifications_none_unread | All already read | Returns 0 |

#### Notification Utility Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| N-018 | test_send_task_reminder | Create reminder notification | Correct message format |
| N-019 | test_send_task_completion_notification | Create completion notification | Correct message format |
| N-020 | test_notification_message_content | Verify message includes task info | task_id and task_name present |

### 5.4 Notification API Tests (Expand test_main.py)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| NA-001 | test_read_notifications_empty | No notifications | 200, empty list |
| NA-002 | test_read_notifications_with_data | Notifications exist | 200, list returned |
| NA-003 | test_read_notifications_unread_only_filter | unread_only=true | Only unread returned |
| NA-004 | test_read_notifications_invalid_filter | unread_only="invalid" | 422 or treat as false |
| NA-005 | test_mark_notification_as_read_api | PATCH valid id | 200 success |
| NA-006 | test_mark_notification_as_read_api_not_found | PATCH invalid id | 404 Not Found |
| NA-007 | test_mark_all_notifications_as_read_api | POST read-all | 200 with count |
| NA-008 | test_get_unread_count_api | Get count | 200 with correct count |
| NA-009 | test_get_unread_count_api_zero | No unread | 200 with count=0 |

### 5.5 Worker Tests (NEW: tests/test_worker.py)

#### Worker Function Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| W-001 | test_check_and_notify_no_tasks | No in_progress tasks | No notifications created |
| W-002 | test_check_and_notify_task_not_due | last_ping recent | No notification created |
| W-003 | test_check_and_notify_task_due | Interval exceeded | Notification created |
| W-004 | test_check_and_notify_updates_last_ping | After notification | last_ping updated |
| W-005 | test_check_and_notify_exactly_at_interval | Edge case | Define behavior |
| W-006 | test_check_and_notify_timezone_handling | UTC vs local | Proper comparison |
| W-007 | test_check_and_notify_naive_datetime | last_ping naive | Converted properly |
| W-008 | test_check_and_notify_multiple_tasks | Multiple due | All get notifications |
| W-009 | test_check_and_notify_mixed_tasks | Some due, some not | Only due get notifications |
| W-010 | test_check_and_notify_zero_interval | interval_minutes=0 | Notification every check |
| W-011 | test_worker_loop_runs | Worker starts and loops | Continuous execution |

#### Worker Error Handling Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| W-012 | test_worker_database_connection_error | DB unavailable | Error logged, continues |
| W-013 | test_worker_notification_creation_error | Notification fails | Error handled, continues |
| W-014 | test_worker_session_rollback_on_error | Failed transaction | Proper rollback |

### 5.6 Integration Tests (NEW: tests/test_integration.py)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| I-001 | test_full_task_lifecycle | Create → Update → Delete | All operations succeed |
| I-002 | test_task_status_transition_flow | todo → in_progress → done | Proper state changes |
| I-003 | test_worker_creates_notification | Worker + task interaction | Notification created |
| I-004 | test_notification_marked_read | Full notification flow | Proper state tracking |
| I-005 | test_task_deletion_with_notifications | Delete task | Notification behavior defined |
| I-006 | test_concurrent_task_updates | Simultaneous edits | No race conditions |

### 5.7 Edge Cases and Boundary Tests

#### Boundary Value Analysis

| Field | Valid Boundaries | Invalid Values |
|-------|-----------------|---------------|
| task.name | 1-255 chars | "", >255 chars |
| task.interval_minutes | 0.1 - 525600 | -1, 0 (if invalid), >525600 |
| task.status | "todo", "in_progress", "done" | "", "invalid", null |
| notification.message | 1-1000 chars | "", >1000 chars |

#### Special Characters and Injection Tests

| Test ID | Input | Expected Behavior |
|---------|-------|-------------------|
| E-001 | name="<script>alert('xss')</script>" | Stored as-is or escaped |
| E-002 | name="'; DROP TABLE tasks; --" | Safe handling, no injection |
| E-003 | name="" | Validation error |
| E-004 | name="   " | Whitespace handling |
| E-005 | name="Task\nWith\nNewlines" | Newline handling |

---

## 6. Test Data Requirements

### 6.1 Fixtures Needed

```python
# tests/conftest.py

import pytest
from sqlmodel import Session, SQLModel, create_engine, StaticPool
from main import Task, get_session, app
from notifications import Notification

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

@pytest.fixture
def session(engine):
    """Create a fresh database session for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def client(session):
    """Create a test client with overridden dependencies."""
    def override_get_session():
        return session
    
    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_task(session):
    """Create a sample task."""
    task = Task(name="Sample Task", interval_minutes=60.0)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

@pytest.fixture
def sample_notification(session):
    """Create a sample notification."""
    notification = Notification(
        task_id=1,
        task_name="Sample Task",
        message="Test message",
        notification_type="reminder",
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
```

### 6.2 Test Data Sets

#### Valid Task Data
```python
VALID_TASKS = [
    {"name": "Simple Task", "interval_minutes": 60.0},
    {"name": "Task with default interval"},  # interval_minutes=60.0
    {"name": "a", "interval_minutes": 0.1},  # minimum reasonable
    {"name": "x" * 255, "interval_minutes": 525600},  # 1 year
    {"name": "Unicode: 任务 📋", "interval_minutes": 30.0},
    {"name": "Special: & < > \" '", "interval_minutes": 45.0},
]
```

#### Invalid Task Data
```python
INVALID_TASKS = [
    {"name": "", "interval_minutes": 60.0},  # empty name
    {"name": "   ", "interval_minutes": 60.0},  # whitespace only
    {"name": "Valid", "interval_minutes": -1},  # negative interval
    {"name": "Valid", "interval_minutes": -0.1},  # negative float
    {"name": "Valid", "interval_minutes": "abc"},  # wrong type
]
```

#### Status Transition Matrix
```python
STATUS_TRANSITIONS = [
    ("todo", "in_progress", True),  # valid
    ("in_progress", "done", True),  # valid
    ("todo", "done", True),  # valid? define business rule
    ("done", "todo", True),  # valid? define business rule
    ("todo", "invalid", False),  # invalid
    ("todo", "", False),  # invalid
]
```

---

## 7. Test Implementation Guide

### 7.1 New Files to Create

1. **tests/conftest.py** - Shared fixtures and configuration
2. **tests/test_task_model.py** - Task model unit tests
3. **tests/test_worker.py** - Worker tests with time mocking
4. **tests/test_integration.py** - End-to-end integration tests
5. **tests/test_edge_cases.py** - Boundary and edge case tests

### 7.2 Required Dependencies

Add to `requirements.txt` or `pyproject.toml`:
```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0
freezegun>=1.2.0
httpx>=0.24.0
```

### 7.3 Worker Test Implementation Example

```python
# tests/test_worker.py
import pytest
from freezegun import freeze_time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from worker import check_and_notify_tasks
from main import Task
from notifications import Notification

class TestWorker:
    @freeze_time("2024-01-01 12:00:00")
    def test_check_and_notify_task_due(self, session):
        """Test notification is created when task is due."""
        # Create task with last_ping 2 hours ago, interval 60 minutes
        task = Task(
            name="Due Task",
            status="in_progress",
            interval_minutes=60.0,
            last_ping=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        session.add(task)
        session.commit()
        
        # Run worker check
        check_and_notify_tasks()
        
        # Verify notification created
        notifications = session.query(Notification).all()
        assert len(notifications) == 1
        assert notifications[0].task_id == task.id
        assert "still in progress" in notifications[0].message
        
        # Verify last_ping updated
        session.refresh(task)
        assert task.last_ping == datetime.now(timezone.utc)
    
    @freeze_time("2024-01-01 12:00:00")
    def test_check_and_notify_task_not_due(self, session):
        """Test no notification when task is not due."""
        # Create task with last_ping 30 minutes ago, interval 60 minutes
        task = Task(
            name="Not Due Task",
            status="in_progress",
            interval_minutes=60.0,
            last_ping=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        session.add(task)
        session.commit()
        
        # Run worker check
        check_and_notify_tasks()
        
        # Verify no notification created
        notifications = session.query(Notification).all()
        assert len(notifications) == 0
    
    def test_check_and_notify_skips_todo_tasks(self, session):
        """Test worker only processes in_progress tasks."""
        task = Task(
            name="Todo Task",
            status="todo",
            interval_minutes=60.0,
        )
        session.add(task)
        session.commit()
        
        check_and_notify_tasks()
        
        notifications = session.query(Notification).all()
        assert len(notifications) == 0
```

### 7.4 Integration Test Example

```python
# tests/test_integration.py
class TestTaskLifecycle:
    def test_complete_task_workflow(self, client, session):
        """Test full lifecycle: create → start → complete → delete."""
        # 1. Create task
        response = client.post("/tasks/", json={
            "name": "Integration Test Task",
            "interval_minutes": 30.0
        })
        assert response.status_code == 200
        task_id = response.json()["id"]
        
        # 2. Start task (todo → in_progress)
        response = client.patch(f"/tasks/{task_id}?status=in_progress")
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
        
        # 3. Complete task (in_progress → done)
        response = client.patch(f"/tasks/{task_id}?status=done")
        assert response.status_code == 200
        assert response.json()["status"] == "done"
        
        # 4. Delete task
        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get("/tasks/")
        assert len(response.json()) == 0
```

### 7.5 Edge Case Test Example

```python
# tests/test_edge_cases.py
import pytest

class TestEdgeCases:
    @pytest.mark.parametrize("name", [
        "a",  # single char
        "a" * 255,  # max reasonable
        "Task with spaces",
        "Task-with-dashes",
        "Task_with_underscores",
        "Task.With.Dots",
        "Task123",
        "123",  # numeric only
        "任务",  # Chinese
        "📋",  # Emoji
        "Mix🚀中文",
    ])
    def test_valid_task_names(self, client, name):
        """Test various valid task name formats."""
        response = client.post("/tasks/", json={"name": name})
        assert response.status_code == 200
        assert response.json()["name"] == name
    
    @pytest.mark.parametrize("invalid_name", [
        "",
        "   ",
        "\t",
        "\n",
    ])
    def test_invalid_task_names(self, client, invalid_name):
        """Test invalid task names are rejected."""
        response = client.post("/tasks/", json={"name": invalid_name})
        assert response.status_code == 422
```

---

## 8. Execution Plan

### 8.1 Implementation Phases

#### Phase 1: Foundation (Week 1)
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Add missing dependencies to requirements
- [ ] Expand task model tests (test_task_model.py)

#### Phase 2: API Coverage (Week 1-2)
- [ ] Expand test_main.py with missing endpoint tests
- [ ] Add error case tests
- [ ] Add boundary tests

#### Phase 3: Notification Module (Week 2)
- [ ] Expand test_notifications.py
- [ ] Add type validation tests
- [ ] Add limit/ordering tests

#### Phase 4: Worker Tests (Week 2-3)
- [ ] Create test_worker.py
- [ ] Add time mocking with freezegun
- [ ] Add error handling tests

#### Phase 5: Integration & Edge Cases (Week 3)
- [ ] Create test_integration.py
- [ ] Create test_edge_cases.py
- [ ] Add concurrent operation tests

#### Phase 6: Optimization (Week 4)
- [ ] Add performance benchmarks
- [ ] Add load tests
- [ ] Review and refactor

### 8.2 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=main --cov=notifications --cov=worker --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m worker

# Run with verbose output
pytest -v

# Run specific file
pytest tests/test_worker.py

# Run specific test
pytest tests/test_main.py::test_create_task

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### 8.3 CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### 8.4 Success Criteria

| Metric | Target |
|--------|--------|
| Code Coverage | >90% |
| Unit Test Pass Rate | 100% |
| Integration Test Pass Rate | 100% |
| Test Execution Time | <30 seconds |
| Flaky Tests | 0 |

---

## 9. Appendix

### 9.1 Current Test Inventory

| File | Tests | Lines | Status |
|------|-------|-------|--------|
| test_main.py | 16 | 298 | Baseline complete |
| test_notifications.py | 12 | 199 | Baseline complete |
| test_worker.py | 0 | 0 | NEEDS CREATION |
| test_integration.py | 0 | 0 | NEEDS CREATION |
| test_edge_cases.py | 0 | 0 | NEEDS CREATION |
| test_task_model.py | 0 | 0 | NEEDS CREATION |

**Total Current Coverage: ~50%**
**Target Coverage: >90%**

### 9.2 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Time constraints | Medium | High | Prioritize critical paths |
| Database state leaks | Low | High | Use fresh session per test |
| Worker timing flaky tests | Medium | Medium | Use freezegun for time mocking |
| Concurrent test failures | Low | Medium | Use isolated in-memory DB |

### 9.3 Maintenance Notes

1. **Adding New Endpoints**: Update test_main.py with corresponding tests
2. **Adding New Models**: Create new test file following existing patterns
3. **Database Schema Changes**: Update fixtures in conftest.py
4. **Dependency Updates**: Verify tests pass after updates

---

*Test Plan Version: 1.0*
*Created: 2024-02-04*
*Status: Ready for Implementation*
