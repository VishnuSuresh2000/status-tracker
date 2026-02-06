# Fixed CI build
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship
from datetime import datetime, timezone
import redis
import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

from contextlib import asynccontextmanager
from notifications import (
    Notification,
    create_db_and_tables as create_notification_tables,
    get_unread_notifications,
    get_all_notifications,
    mark_notification_as_read as mark_notif_as_read,
    mark_all_notifications_as_read as mark_all_notifs_as_read,
)

# Database setup
DATABASE_URL = "sqlite:///./data/tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# ============================================================================
# DATABASE MODELS
# ============================================================================


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    priority: str = Field(default="medium")  # low, medium, high, critical
    due_date: Optional[datetime] = Field(default=None)
    progress_percent: int = Field(default=0)  # 0-100
    flow_chart: Optional[str] = Field(default=None)  # JSON or mermaid diagram
    context_tags: Optional[str] = Field(default=None)  # Comma-separated tags
    definition_of_done: Optional[str] = Field(default=None)
    last_ai_summary: Optional[str] = Field(default=None)
    last_ping: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # New fields for Rich Info
    agent_name: str = Field(default="Main Agent")
    skills: Optional[str] = Field(default=None)

    # Legacy fields
    status: str = Field(default="todo")
    interval_minutes: Optional[float] = Field(default=60.0)

    # Relationships
    phases: List["Phase"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: List["Comment"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Phase(SQLModel, table=True):
    __tablename__ = "phases"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None) # New field
    status: str = Field(
        default="not_started"
    )  # not_started, in_progress, completed, blocked
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    task: Task = Relationship(back_populates="phases")
    todos: List["Todo"] = Relationship(back_populates="phase")


class Todo(SQLModel, table=True):
    __tablename__ = "todos"

    id: Optional[int] = Field(default=None, primary_key=True)
    phase_id: int = Field(foreign_key="phases.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None) # New field
    status: str = Field(default="todo")  # todo, in_progress, done
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    phase: Phase = Relationship(back_populates="todos")


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    text: str
    author: str = Field(default="system")  # system, user, agent, sub-agent
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    task: Task = Relationship(back_populates="comments")


# ============================================================================
# PYDANTIC SCHEMAS (DTOs)
# ============================================================================


# Todo Schemas
class TodoBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "todo"


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    status: str


class TodoRead(TodoBase):
    id: int
    phase_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Phase Schemas
class PhaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "not_started"
    order: int = 0


class PhaseCreate(PhaseBase):
    todos: Optional[List[TodoCreate]] = []


class PhaseUpdate(BaseModel):
    status: str


class PhaseRead(PhaseBase):
    id: int
    task_id: int
    created_at: datetime
    todos: List[TodoRead] = []

    class Config:
        from_attributes = True


# Comment Schemas
class CommentBase(BaseModel):
    text: str
    author: str = "system"


class CommentCreate(CommentBase):
    pass


class CommentRead(CommentBase):
    id: int
    task_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Task Schemas
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str = "medium"
    interval_minutes: Optional[float] = 60.0
    due_date: Optional[datetime] = None
    flow_chart: Optional[str] = None
    context_tags: Optional[str] = None
    definition_of_done: Optional[str] = None
    agent_name: str = "Main Agent"
    skills: Optional[str] = None


class TaskCreate(TaskBase):
    phases: Optional[List[PhaseCreate]] = []


class TaskRead(TaskBase):
    id: int
    status: str = "todo"
    progress_percent: int
    last_ai_summary: Optional[str]
    last_ping: datetime
    created_at: datetime
    phases: List[PhaseRead] = []
    comments: List[CommentRead] = []
    unread_reminder_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# DATABASE SETUP
# ============================================================================


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def migrate_null_statuses():
    """Migrate existing null status values to correct values based on progress."""
    from sqlalchemy import text

    with Session(engine) as session:
        # Find all tasks with null status using raw SQL
        result = session.exec(
            text("SELECT id, progress_percent FROM tasks WHERE status IS NULL")
        )
        tasks_to_fix = result.all()

        for row in tasks_to_fix:
            task_id = row[0]
            progress = row[1]

            # Determine correct status based on progress
            if progress >= 100:
                new_status = "done"
            elif progress > 0:
                new_status = "in_progress"
            else:
                new_status = "todo"

            # Update the task using raw SQL execution
            update_stmt = text("UPDATE tasks SET status = :status WHERE id = :id")
            session.execute(update_stmt, {"status": new_status, "id": task_id})

        if tasks_to_fix:
            session.commit()
            print(f"Migrated {len(tasks_to_fix)} tasks with null status")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_unread_reminder_count(task_id: int, session: Session) -> int:
    """Count unread reminder notifications for a specific task."""
    statement = (
        select(Notification)
        .where(Notification.task_id == task_id)
        .where(Notification.is_read == False)
        .where(Notification.notification_type == "reminder")
    )
    results = session.exec(statement).all()
    return len(results)


def calculate_task_progress(task_id: int, session: Session) -> int:
    """
    Calculate task progress based on phases and todos.
    """
    task = session.get(Task, task_id)
    if not task or not task.phases:
        return 0

    phases = task.phases
    phase_weight = 100 / len(phases)
    total_progress = 0.0

    for phase in phases:
        if phase.status == "completed":
            total_progress += phase_weight
        elif phase.status == "in_progress":
            todos = phase.todos
            if todos:
                completed = sum(1 for t in todos if t.status == "done")
                total_progress += phase_weight * (completed / len(todos))
        elif phase.status == "not_started":
            todos = phase.todos
            if todos:
                completed = sum(1 for t in todos if t.status == "done")
                if completed > 0:
                    total_progress += phase_weight * (completed / len(todos))

    return round(total_progress)


def recalculate_task_progress(task_id: int, session: Session) -> None:
    """Recalculate and update task progress and sync legacy status for UI."""
    task = session.get(Task, task_id)
    if task:
        task.progress_percent = calculate_task_progress(task_id, session)

        # Sync legacy status field for UI column sorting
        if task.progress_percent >= 100:
            task.status = "done"
        elif task.progress_percent > 0:
            task.status = "in_progress"
        else:
            task.status = "todo"

        session.add(task)
        session.commit()


def create_system_comment(task_id: int, text: str, session: Session) -> Comment:
    """Create a system comment for logging."""
    comment = Comment(task_id=task_id, text=text, author="system")
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


def update_phase_status_from_todos(phase_id: int, session: Session) -> None:
    """Update phase status based on its todos."""
    phase = session.get(Phase, phase_id)
    if not phase or not phase.todos:
        return

    todos = phase.todos
    done_count = sum(1 for t in todos if t.status == "done")
    in_progress_count = sum(1 for t in todos if t.status == "in_progress")

    old_status = phase.status
    if done_count == len(todos):
        new_status = "completed"
    elif done_count > 0 or in_progress_count > 0:
        new_status = "in_progress"
    else:
        new_status = "not_started"

    if phase.status != new_status and phase.status != "blocked":
        phase.status = new_status
        session.add(phase)
        session.commit()
        create_system_comment(
            phase.task_id,
            f"Phase '{phase.name}' status changed from '{old_status}' to '{phase.status}'",
            session,
        )

    recalculate_task_progress(phase.task_id, session)


def update_todos_when_phase_completed(phase_id: int, session: Session) -> None:
    """Mark all todos as done when phase is marked completed."""
    phase = session.get(Phase, phase_id)
    if not phase:
        return

    for todo in phase.todos:
        if todo.status != "done":
            todo.status = "done"
            session.add(todo)

    session.commit()


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    create_notification_tables()
    migrate_null_statuses()
    yield


app = FastAPI(title="Status Tracker", lifespan=lifespan)

# Redis for background tasks
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# Security
security = HTTPBearer()
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify that the request is from an authorized sub-agent."""
    if not API_AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="API_AUTH_TOKEN not configured")
    if credentials.credentials != API_AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_session():
    with Session(engine) as session:
        yield session


# ============================================================================
# STATIC FILES
# ============================================================================


@app.get("/")
async def serve_index():
    """Serve the index.html file at the root path."""
    return FileResponse("index.html")


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.post("/tasks/", response_model=TaskRead)
def create_task(
    task_data: TaskCreate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Create a task with optional nested phases and todos."""
    task = Task(
        name=task_data.name,
        description=task_data.description,
        priority=task_data.priority,
        interval_minutes=task_data.interval_minutes,
        due_date=task_data.due_date,
        flow_chart=task_data.flow_chart,
        context_tags=task_data.context_tags,
        definition_of_done=task_data.definition_of_done,
        agent_name=task_data.agent_name,
        skills=task_data.skills,
        progress_percent=0,
        status="todo",
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    for phase_data in task_data.phases or []:
        phase = Phase(
            task_id=task.id,
            name=phase_data.name,
            description=phase_data.description,
            status=phase_data.status,
            order=phase_data.order,
        )
        session.add(phase)
        session.commit()
        session.refresh(phase)

        for todo_data in phase_data.todos or []:
            todo = Todo(
                phase_id=phase.id,
                name=todo_data.name,
                description=todo_data.description,
                status=todo_data.status,
            )
            session.add(todo)

        session.commit()
        session.refresh(phase)
        update_phase_status_from_todos(phase.id, session)

    recalculate_task_progress(task.id, session)
    session.refresh(task)
    create_system_comment(task.id, f"Task '{task.name}' created", session)

    return task


@app.get("/tasks/", response_model=List[TaskRead])
def read_tasks(session: Session = Depends(get_session)):
    """Get all tasks with their phases, todos, and comments."""
    tasks = session.exec(select(Task)).all()
    results = []
    for task in tasks:
        # Create TaskRead object manually to include calculated field
        task_data = task.model_dump()
        task_data["phases"] = [p.model_dump(include={"id", "task_id", "name", "status", "order", "created_at", "todos"}) for p in task.phases]
        # Ensure todos are also dumped
        for p_idx, phase in enumerate(task.phases):
            task_data["phases"][p_idx]["todos"] = [t.model_dump() for t in phase.todos]
        
        task_data["comments"] = [c.model_dump() for c in task.comments]
        task_data["unread_reminder_count"] = get_unread_reminder_count(task.id, session)
        results.append(TaskRead(**task_data))
    return results


@app.get("/tasks/{task_id}", response_model=TaskRead)
def read_task(task_id: int, session: Session = Depends(get_session)):
    """Get a specific task with full hierarchy."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = task.model_dump()
    task_data["phases"] = [p.model_dump() for p in task.phases]
    for p_idx, phase in enumerate(task.phases):
        task_data["phases"][p_idx]["todos"] = [t.model_dump() for t in phase.todos]
    
    task_data["comments"] = [c.model_dump() for c in task.comments]
    task_data["unread_reminder_count"] = get_unread_reminder_count(task.id, session)
    
    return TaskRead(**task_data)


@app.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Update task status (legacy endpoint)."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if status:
        task.status = status
        task.last_ping = datetime.now(timezone.utc)
        session.add(task)
        session.commit()
        session.refresh(task)
        create_system_comment(task_id, f"Task status updated to '{status}'", session)

    return task


@app.delete("/tasks/{task_id}", response_model=dict)
def delete_task(
    task_id: int,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Delete a task and all its phases, todos, and comments."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session.delete(task)
    session.commit()
    return {"message": "Task deleted successfully", "task_id": task_id}


@app.put("/tasks/{task_id}", response_model=TaskRead)
def edit_task(
    task_id: int,
    name: Optional[str] = None,
    interval_minutes: Optional[float] = None,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Edit task fields (legacy endpoint)."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if name is not None:
        task.name = name
    if interval_minutes is not None:
        task.interval_minutes = interval_minutes

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.post("/tasks/{task_id}/batch-report", response_model=dict)
def batch_report(
    task_id: int,
    reports: List[dict],
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Process multiple updates (comments or status updates) in one transaction."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for report in reports:
        # 1. Handle Comments
        if "comment" in report:
            comment = Comment(
                task_id=task_id,
                text=report["comment"],
                author=report.get("author", "sub-agent"),
            )
            session.add(comment)
        
        # 2. Handle Todo Status Updates
        if "todo_id" in report and "status" in report:
            todo = session.get(Todo, report["todo_id"])
            if todo:
                old_status = todo.status
                todo.status = report["status"]
                session.add(todo)
                
                # Propagate to phase
                update_phase_status_from_todos(todo.phase_id, session)
                
                create_system_comment(
                    task_id,
                    f"Todo '{todo.name}' status updated to '{todo.status}' via batch report",
                    session
                )

        # 3. Handle Phase Status Updates
        if "phase_id" in report and "status" in report:
            phase = session.get(Phase, report["phase_id"])
            if phase:
                old_status = phase.status
                phase.status = report["status"]
                session.add(phase)
                
                if phase.status == "completed":
                    update_todos_when_phase_completed(phase.id, session)
                
                create_system_comment(
                    task_id,
                    f"Phase '{phase.name}' status updated to '{phase.status}' via batch report",
                    session
                )

        # 4. Handle Task Status Update (legacy/direct)
        if "task_status" in report:
            new_status = report["task_status"]
            task.status = new_status
            task.last_ping = datetime.now(timezone.utc)
            session.add(task)
            create_system_comment(task_id, f"Task status updated to '{task.status}' via batch report", session)
            
            # Auto-complete phases if task is done
            if new_status == "done":
                for phase in task.phases:
                    if phase.status != "completed":
                        phase.status = "completed"
                        session.add(phase)
                        update_todos_when_phase_completed(phase.id, session)

    session.commit()
    recalculate_task_progress(task_id, session)
    return {"message": "Batch report processed successfully"}


@app.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Update todo status and propagate to phase and task."""
    todo = session.get(Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    old_status = todo.status
    todo.status = todo_update.status
    session.add(todo)
    session.commit()
    session.refresh(todo)

    phase = session.get(Phase, todo.phase_id)
    if phase:
        create_system_comment(
            phase.task_id,
            f"Todo '{todo.name}' status changed from '{old_status}' to '{todo.status}'",
            session,
        )
        update_phase_status_from_todos(todo.phase_id, session)

    return todo


@app.patch("/phases/{phase_id}", response_model=PhaseRead)
def update_phase(
    phase_id: int,
    phase_update: PhaseUpdate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Update phase status and propagate to task."""
    phase = session.get(Phase, phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")

    old_status = phase.status
    phase.status = phase_update.status
    session.add(phase)
    session.commit()
    session.refresh(phase)

    if phase.status == "completed":
        update_todos_when_phase_completed(phase_id, session)

    create_system_comment(
        phase.task_id,
        f"Phase '{phase.name}' status changed from '{old_status}' to '{phase.status}'",
        session,
    )

    recalculate_task_progress(phase.task_id, session)
    return phase


@app.post("/tasks/{task_id}/comments", response_model=CommentRead)
def add_comment(
    task_id: int,
    comment_data: CommentCreate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Add a manual comment to a task."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = Comment(
        task_id=task_id,
        text=comment_data.text,
        author=comment_data.author,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@app.get("/tasks/{task_id}/comments", response_model=List[CommentRead])
def read_comments(
    task_id: int,
    session: Session = Depends(get_session),
):
    """Get all comments for a task."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.comments


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================


@app.get("/notifications/", response_model=List[Notification])
def read_notifications(
    unread_only: bool = False, session: Session = Depends(get_session)
):
    """Get all notifications."""
    if unread_only:
        return get_unread_notifications(session)
    return get_all_notifications(session)


@app.patch("/notifications/{notification_id}/read", response_model=dict)
def mark_as_read(
    notification_id: int,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Mark a notification as read."""
    if not mark_notif_as_read(notification_id, session):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {
        "message": "Notification marked as read",
        "notification_id": notification_id,
    }


@app.post("/notifications/read-all", response_model=dict)
def mark_all_read(
    session: Session = Depends(get_session), token: str = Depends(verify_token)
):
    """Mark all notifications as read."""
    count = mark_all_notifs_as_read(session)
    return {"message": f"{count} notifications marked as read"}


@app.get("/notifications/unread-count", response_model=dict)
def get_unread_count(session: Session = Depends(get_session)):
    """Get count of unread notifications."""
    notifications = get_unread_notifications(session)
    return {"unread_count": len(notifications)}
