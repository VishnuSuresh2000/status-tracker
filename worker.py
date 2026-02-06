import time
import os
from sqlmodel import Session, create_engine, select
from main import Task
from datetime import datetime, timezone, timedelta
from notifications import send_task_reminder, send_task_completion_notification

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tasks.db")
engine = create_engine(DATABASE_URL)


def check_and_notify_tasks():
    """Check for tasks that need notifications and send them."""
    try:
        with Session(engine) as session:
            now = datetime.now(timezone.utc)
            statement = select(Task).where(Task.status == "in_progress")
            tasks = session.exec(statement).all()

            for task in tasks:
                # Ensure last_ping is timezone aware for comparison
                last_ping = task.last_ping
                if last_ping.tzinfo is None:
                    last_ping = last_ping.replace(tzinfo=timezone.utc)
                
                if now > last_ping + timedelta(minutes=task.interval_minutes):
                    # Send notification
                    if task.id is not None:
                        notification = send_task_reminder(task.id, task.name)
                        print(f"[NOTIFICATION] Created: {notification.message}")

                    # Update last_ping to avoid spamming
                    task.last_ping = now
                    session.add(task)
                    session.commit()
    except Exception as e:
        print(f"[ERROR] Worker loop error: {e}")


def worker():
    print("[WORKER] Notification worker started...")
    print("[WORKER] Checking for in-progress tasks every 30 seconds")

    while True:
        check_and_notify_tasks()
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    worker()
