from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import desc
from datetime import datetime, timezone
from typing import Optional, List
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tasks.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    task_name: str
    message: str
    notification_type: str = Field(default="reminder")  # reminder, completion, system
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def add_notification(
    task_id: int, task_name: str, message: str, notification_type: str = "reminder"
) -> Notification:
    with Session(engine) as session:
        notification = Notification(
            task_id=task_id,
            task_name=task_name,
            message=message,
            notification_type=notification_type,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)
        return notification


def get_unread_notifications(session: Session) -> List[Notification]:
    statement = (
        select(Notification)
        .where(Notification.is_read == False)
        .order_by(desc(Notification.created_at))
    )
    result = session.exec(statement).all()
    return list(result)


def get_all_notifications(session: Session, limit: int = 50) -> List[Notification]:
    statement = (
        select(Notification).order_by(desc(Notification.created_at)).limit(limit)
    )
    result = session.exec(statement).all()
    return list(result)


def mark_notification_as_read(notification_id: int, session: Session) -> bool:
    notification = session.get(Notification, notification_id)
    if not notification:
        return False
    notification.is_read = True
    session.add(notification)
    session.commit()
    return True


def mark_all_notifications_as_read(session: Session) -> int:
    statement = select(Notification).where(Notification.is_read == False)
    notifications = session.exec(statement).all()
    count = 0
    for notification in notifications:
        notification.is_read = True
        session.add(notification)
        count += 1
    session.commit()
    return count


def send_task_reminder(task_id: int, task_name: str):
    message = (
        f"Task '{task_name}' (ID: {task_id}) is still in progress and needs attention!"
    )
    notification = add_notification(task_id, task_name, message, "reminder")
    return notification


def send_task_completion_notification(task_id: int, task_name: str):
    message = f"Task '{task_name}' has been completed!"
    notification = add_notification(task_id, task_name, message, "completion")
    return notification
