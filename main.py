from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    mark_notification_as_read,
    mark_all_notifications_as_read,
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

    # Legacy fields (for backwards compatibility)
    status: Optional[str] = Field(default=None)  # Deprecated: use phases instead
    interval_minutes: Optional[float] = Field(default=None)  # Deprecated

    # Relationships
    phases: List["Phase"] = Relationship(back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    comments: List["Comment"] = Relationship(back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Phase(SQLModel, table=True):
    __tablename__ = "phases"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    name: str = Field(index=True)
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
    status: str = Field(default="todo")  # todo, in_progress, done
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    phase: Phase = Relationship(back_populates="todos")


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    text: str
    author: str = Field(default="system")  # system, user, agent
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    task: Task = Relationship(back_populates="comments")


# ============================================================================
# PYDANTIC SCHEMAS (DTOs)
# ============================================================================


# Todo Schemas
class TodoBase(BaseModel):
    name: str
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


class TaskCreate(TaskBase):
    phases: Optional[List[PhaseCreate]] = []


class TaskRead(TaskBase):
    id: int
    progress_percent: int
    last_ai_summary: Optional[str]
    last_ping: datetime
    created_at: datetime
    phases: List[PhaseRead] = []
    comments: List[CommentRead] = []

    class Config:
        from_attributes = True


# ============================================================================
# DATABASE SETUP
# ============================================================================


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def calculate_task_progress(task_id: int, session: Session) -> int:
    """
    Calculate task progress based on phases and todos.

    Algorithm:
    1. Each phase has equal weight (100% / num_phases)
    2. Phase progress = (completed_todos / total_todos) * phase_weight
    3. If phase is completed, it contributes full phase_weight
    4. If phase is blocked, it contributes 0
    """
    task = session.get(Task, task_id)
    if not task:
        return 0

    phases = task.phases

    if not phases:
        return 0

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
        elif phase.status == "blocked":
            pass  # Contributes 0
        elif phase.status == "not_started":
            # Calculate based on todo progress even if phase not marked in_progress
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

    # Always recalculate task progress when a todo status changes, 
    # even if the phase status itself didn't change
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
# API ENDPOINTS
# ============================================================================


@app.post("/tasks/", response_model=TaskRead)
def create_task(
    task_data: TaskCreate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Create a task with optional nested phases and todos."""
    # Create the task
    task = Task(
        name=task_data.name,
        description=task_data.description,
        priority=task_data.priority,
        interval_minutes=task_data.interval_minutes,
        due_date=task_data.due_date,
        flow_chart=task_data.flow_chart,
        context_tags=task_data.context_tags,
        definition_of_done=task_data.definition_of_done,
        progress_percent=0,
        status="todo"
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    # Create phases and todos
    assert task.id is not None, "Task ID should be set after commit"
    for phase_data in task_data.phases or []:
        phase = Phase(
            task_id=task.id,
            name=phase_data.name,
            status=phase_data.status,
            order=phase_data.order,
        )
        session.add(phase)
        session.commit()
        session.refresh(phase)

        # Create todos for this phase
        assert phase.id is not None, "Phase ID should be set after commit"
        for todo_data in phase_data.todos or []:
            todo = Todo(
                phase_id=phase.id,
                name=todo_data.name,
                status=todo_data.status,
            )
            session.add(todo)

        session.commit()
        session.refresh(phase)

        # Auto-update phase status based on todos
        update_phase_status_from_todos(phase.id, session)

    # Calculate initial progress
    recalculate_task_progress(task.id, session)
    session.refresh(task)

    # Create system comment
    create_system_comment(task.id, f"Task '{task.name}' created", session)

    return task


@app.get("/tasks/", response_model=List[TaskRead])
def read_tasks(session: Session = Depends(get_session)):
    """Get all tasks with their phases, todos, and comments."""
    tasks = session.exec(select(Task)).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskRead)
def read_task(task_id: int, session: Session = Depends(get_session)):
    """Get a specific task with full hierarchy."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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


@app.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    session: Session = Depends(get_session),
):
    """Update todo status and trigger progress recalculation."""
    todo = session.get(Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    old_status = todo.status
    todo.status = todo_update.status
    session.add(todo)
    session.commit()
    session.refresh(todo)

    # Trigger status propagation and progress recalculation
    update_phase_status_from_todos(todo.phase_id, session)

    # Log the change
    phase = session.get(Phase, todo.phase_id)
    if phase:
        create_system_comment(
            phase.task_id,
            f"Todo '{todo.name}' updated: {old_status} -> {todo.status}",
            session,
        )

    return todo


@app.patch("/phases/{phase_id}", response_model=PhaseRead)
def update_phase(
    phase_id: int,
    phase_update: PhaseUpdate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Update phase status and trigger progress recalculation."""
    phase = session.get(Phase, phase_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")

    old_status = phase.status
    phase.status = phase_update.status
    session.add(phase)

    # If marking as completed, mark all todos as done
    if phase.status == "completed":
        update_todos_when_phase_completed(phase_id, session)

    session.commit()
    session.refresh(phase)

    # Trigger progress recalculation
    recalculate_task_progress(phase.task_id, session)

    # Log the change
    create_system_comment(
        phase.task_id,
        f"Phase '{phase.name}' updated: {old_status} -> {phase.status}",
        session,
    )

    return phase


@app.post("/tasks/{task_id}/comments", response_model=CommentRead)
def add_comment(
    task_id: int,
    comment_data: CommentCreate,
    session: Session = Depends(get_session),
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
def read_task_comments(task_id: int, session: Session = Depends(get_session)):
    """Get all comments for a specific task."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.comments


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================


@app.get("/notifications/", response_model=List[Notification])
def read_notifications(unread_only: bool = False):
    """Get notifications."""
    if unread_only:
        return get_unread_notifications()
    return get_all_notifications()


@app.get("/notifications/unread-count")
def read_unread_count():
    """Get count of unread notifications."""
    return {"count": len(get_unread_notifications())}


@app.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int):
    """Mark a notification as read."""
    if mark_notification_as_read(notification_id):
        return {"message": "Notification marked as read"}
    raise HTTPException(status_code=404, detail="Notification not found")


@app.post("/notifications/read-all")
def mark_all_read():
    """Mark all notifications as read."""
    mark_all_notifications_as_read()
    return {"message": "All notifications marked as read"}
