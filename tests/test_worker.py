import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from sqlmodel import Session
from worker import check_and_notify_tasks
from main import Task

@pytest.fixture
def mock_session():
    with patch("worker.Session") as mock:
        session = MagicMock(spec=Session)
        mock.return_value.__enter__.return_value = session
        yield session

@pytest.fixture
def mock_send_reminder():
    with patch("worker.send_task_reminder") as mock:
        yield mock

def test_check_and_notify_tasks_sends_reminder(mock_session, mock_send_reminder):
    # Setup: A task that is in_progress and overdue
    now = datetime.now(timezone.utc)
    last_ping = now - timedelta(minutes=61)
    task = Task(
        id=1,
        name="Overdue Task",
        status="in_progress",
        interval_minutes=60.0,
        last_ping=last_ping
    )
    
    mock_session.exec.return_value.all.return_value = [task]
    
    # Execute
    with patch("worker.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        mock_datetime.utcfromtimestamp = datetime.utcfromtimestamp
        mock_datetime.combine = datetime.combine
        mock_datetime.strptime = datetime.strptime
        mock_datetime.min = datetime.min
        mock_datetime.max = datetime.max
        # Mocking datetime.now(timezone.utc) is tricky, worker.py uses datetime.now(timezone.utc)
        check_and_notify_tasks()
    
    # Verify
    mock_send_reminder.assert_called_once_with(1, "Overdue Task")
    assert task.last_ping == now
    mock_session.add.assert_called_once_with(task)
    mock_session.commit.assert_called_once()

def test_check_and_notify_tasks_no_reminder_if_not_due(mock_session, mock_send_reminder):
    # Setup: A task that is in_progress but not yet due
    now = datetime.now(timezone.utc)
    last_ping = now - timedelta(minutes=30)
    task = Task(
        id=2,
        name="Not Due Task",
        status="in_progress",
        interval_minutes=60.0,
        last_ping=last_ping
    )
    
    mock_session.exec.return_value.all.return_value = [task]
    
    # Execute
    with patch("worker.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        check_and_notify_tasks()
    
    # Verify
    mock_send_reminder.assert_not_called()
    assert task.last_ping == last_ping
    mock_session.add.assert_not_called()

def test_check_and_notify_tasks_handles_naive_datetime(mock_session, mock_send_reminder):
    # Setup: A task with a naive datetime (it should be converted to UTC)
    now = datetime.now(timezone.utc)
    last_ping_naive = datetime.now() - timedelta(minutes=120)
    task = Task(
        id=3,
        name="Naive Datetime Task",
        status="in_progress",
        interval_minutes=60.0,
        last_ping=last_ping_naive
    )
    
    mock_session.exec.return_value.all.return_value = [task]
    
    # Execute
    with patch("worker.datetime") as mock_datetime:
        mock_datetime.now.return_value = now
        check_and_notify_tasks()
    
    # Verify
    mock_send_reminder.assert_called_once()
    assert task.last_ping == now
