import time
import os
from sqlmodel import Session, create_engine, select
from sqlalchemy import desc
from main import Agent, Task, TaskAssignment
from datetime import datetime, timezone, timedelta
from typing import List, Optional
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

                if now > last_ping + timedelta(minutes=task.interval_minutes or 60):
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


class PingWorker:
    def __init__(self, interval_seconds=30):
        self.interval_seconds = interval_seconds
        print(f"[PING_WORKER] Initialized with {interval_seconds}s interval")

    def run(self):
        print("[PING_WORKER] Starting ping worker...")
        while True:
            try:
                with Session(engine) as session:
                    tasks = self.get_tasks_with_ping_enabled(session)
                    for task in tasks:
                        self.check_task_ping(task, session)
            except Exception as e:
                print(f"[PING_WORKER] Error in main loop: {e}")
            time.sleep(self.interval_seconds)

    def get_tasks_with_ping_enabled(self, session: Session) -> List[Task]:
        statement = select(Task).where(Task.is_ping_enabled == True)
        return session.exec(statement).all()

    def get_available_agents(self, session: Session) -> List[Agent]:
        statement = select(Agent).where(Agent.is_active == True)
        return session.exec(statement).all()

    def get_latest_assignment(
        self, task_id: int, session: Session
    ) -> Optional[TaskAssignment]:
        statement = (
            select(TaskAssignment)
            .where(TaskAssignment.task_id == task_id)
            .order_by(desc(TaskAssignment.assigned_at))
            .limit(1)
        )
        return session.exec(statement).first()

    def get_main_agent(self, name: str, session: Session) -> Optional[Agent]:
        statement = select(Agent).where(Agent.name == name, Agent.type == "main_agent")
        return session.exec(statement).first()

    def check_task_ping(self, task: Task, session: Session):
        now = datetime.now(timezone.utc)
        last_ping = task.last_ping
        if last_ping.tzinfo is None:
            last_ping = last_ping.replace(tzinfo=timezone.utc)

        ping_threshold = last_ping + timedelta(minutes=task.ping_interval_minutes or 30)

        if now > ping_threshold:
            if task.assigned_agent_id:
                agent = session.get(Agent, task.assigned_agent_id)
                if agent and self.is_agent_timed_out(agent, session):
                    if agent.type == "sub_agent":
                        print(
                            f"[PING_WORKER] Sub-agent {agent.name} timed out, escalating to Ruto"
                        )
                        self.escalate_task(task, agent, None, session)
                    elif agent.type == "main_agent":
                        print(f"[PING_WORKER] Main agent {agent.name} not responding")
                        # Mark as not responding in UI - this would be handled by the frontend
                        # We could add a status field to track this
            else:
                # No agent assigned, auto-assign
                self.auto_assign_task(task, session)

    def auto_assign_task(self, task: Task, session: Session):
        available_agents = self.get_available_agents(session)
        if available_agents:
            agent = available_agents[0]  # Simple selection - could be improved
            task.assigned_agent_id = agent.id
            task.last_agent_acknowledgment = datetime.now(timezone.utc)
            session.add(task)
            session.commit()
            print(f"[PING_WORKER] Auto-assigned task {task.name} to {agent.name}")

    def escalate_task(
        self, task: Task, from_agent: Agent, to_agent: Optional[Agent], session: Session
    ):
        if to_agent is None:
            # Find Ruto (main agent)
            ruto = self.get_main_agent("Ruto", session)
            if ruto:
                to_agent = ruto
            else:
                print(f"[PING_WORKER] Could not find main agent for escalation")
                return

        # Create new assignment
        assignment = TaskAssignment(
            task_id=task.id,
            agent_id=to_agent.id,
            original_agent_id=from_agent.id,
            escalation_count=1,
            status="pending",
        )
        session.add(assignment)

        # Update task assignment
        task.assigned_agent_id = to_agent.id
        task.last_agent_acknowledgment = None
        task.last_ping = datetime.now(timezone.utc)
        session.add(task)
        session.commit()

        print(
            f"[PING_WORKER] Escalated task {task.name} from {from_agent.name} to {to_agent.name}"
        )

    def is_agent_timed_out(self, agent: Agent, session: Session) -> bool:
        if not agent.last_acknowledgment:
            return True

        now = datetime.now(timezone.utc)
        timeout_threshold = agent.last_acknowledgment + timedelta(
            minutes=agent.timeout_minutes
        )
        return now > timeout_threshold


def worker():
    print("[WORKER] Notification worker started...")
    print("[WORKER] Checking for in-progress tasks every 30 seconds")

    while True:
        check_and_notify_tasks()
        time.sleep(30)  # Check every 30 seconds


if __name__ == "__main__":
    worker()
