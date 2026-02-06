import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from main import app, get_session, Task, Notification
from datetime import datetime, timezone

# Setup in-memory database for testing
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

def test_unread_reminder_count_logic(client: TestClient, session: Session):
    # 1. Create a task
    task = Task(name="Test Task", status="in_progress")
    session.add(task)
    session.commit()
    session.refresh(task)
    
    # 2. Verify initial count is 0
    response = client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    assert response.json()["unread_reminder_count"] == 0
    
    # 3. Add one reminder notification
    notif1 = Notification(
        task_id=task.id,
        task_name=task.name,
        message="Ping 1",
        notification_type="reminder",
        is_read=False
    )
    session.add(notif1)
    session.commit()
    
    # 4. Verify count is 1
    response = client.get(f"/tasks/{task.id}")
    assert response.json()["unread_reminder_count"] == 1
    
    # 5. Add another reminder notification
    notif2 = Notification(
        task_id=task.id,
        task_name=task.name,
        message="Ping 2",
        notification_type="reminder",
        is_read=False
    )
    session.add(notif2)
    session.commit()
    
    # 6. Verify count is 2
    response = client.get(f"/tasks/{task.id}")
    assert response.json()["unread_reminder_count"] == 2
    
    # 7. Mark one as read
    notif1.is_read = True
    session.add(notif1)
    session.commit()
    
    # 8. Verify count is 1
    response = client.get(f"/tasks/{task.id}")
    assert response.json()["unread_reminder_count"] == 1
    
    # 9. Add a non-reminder notification
    notif3 = Notification(
        task_id=task.id,
        task_name=task.name,
        message="Completion",
        notification_type="completion",
        is_read=False
    )
    session.add(notif3)
    session.commit()
    
    # 10. Verify count is still 1 (only reminders count)
    response = client.get(f"/tasks/{task.id}")
    assert response.json()["unread_reminder_count"] == 1

def test_unread_reminder_count_in_list(client: TestClient, session: Session):
    # 1. Create two tasks
    task1 = Task(name="Task 1", status="in_progress")
    task2 = Task(name="Task 2", status="in_progress")
    session.add(task1)
    session.add(task2)
    session.commit()
    
    # 2. Add reminders to task 1
    session.add(Notification(task_id=task1.id, task_name=task1.name, message="T1 P1", notification_type="reminder"))
    session.add(Notification(task_id=task1.id, task_name=task1.name, message="T1 P2", notification_type="reminder"))
    
    # 3. Add one reminder to task 2
    session.add(Notification(task_id=task2.id, task_name=task2.name, message="T2 P1", notification_type="reminder"))
    session.commit()
    
    # 4. Verify list response
    response = client.get("/tasks/")
    assert response.status_code == 200
    data = response.json()
    
    t1_data = next(t for t in data if t["id"] == task1.id)
    t2_data = next(t for t in data if t["id"] == task2.id)
    
    assert t1_data["unread_reminder_count"] == 2
    assert t2_data["unread_reminder_count"] == 1
