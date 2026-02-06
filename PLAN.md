# Status Tracker - Nested Structure Upgrade Plan

## Overview

Upgrade Status Tracker to support hierarchical task management with **Tasks → Phases → Todos**, plus **Comments** for logging.

## Phase 1: Database Schema Design

### 1.1 Updated Task Model

```python
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
    
    # Relationships
    phases: List["Phase"] = Relationship(back_populates="task")
    comments: List["Comment"] = Relationship(back_populates="task")
```

### 1.2 New Phase Model

```python
class Phase(SQLModel, table=True):
    __tablename__ = "phases"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    name: str = Field(index=True)
    status: str = Field(default="not_started")  # not_started, in_progress, completed, blocked
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    task: Task = Relationship(back_populates="phases")
    todos: List["Todo"] = Relationship(back_populates="phase")
```

### 1.3 New Todo Model

```python
class Todo(SQLModel, table=True):
    __tablename__ = "todos"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phase_id: int = Field(foreign_key="phases.id", index=True)
    name: str = Field(index=True)
    status: str = Field(default="todo")  # todo, in_progress, done
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    phase: Phase = Relationship(back_populates="todos")
```

### 1.4 New Comment Model

```python
class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    text: str
    author: str = Field(default="system")  # system, user, agent
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    task: Task = Relationship(back_populates="comments")
```

## Phase 2: API Endpoints

### 2.1 POST /tasks/ - Create Task with Nested Structure

**Request Body:**
```json
{
  "name": "Project Alpha",
  "description": "Major feature implementation",
  "priority": "high",
  "due_date": "2026-03-01T00:00:00Z",
  "progress_percent": 0,
  "flow_chart": "graph TD; A[Start] --> B[Phase 1]; B --> C[Phase 2];",
  "context_tags": "backend,api,critical",
  "definition_of_done": "All phases complete, tests passing",
  "phases": [
    {
      "name": "Planning",
      "status": "completed",
      "order": 1,
      "todos": [
        {"name": "Define requirements", "status": "done"},
        {"name": "Create wireframes", "status": "done"}
      ]
    },
    {
      "name": "Development",
      "status": "in_progress",
      "order": 2,
      "todos": [
        {"name": "Setup project", "status": "done"},
        {"name": "Implement API", "status": "in_progress"},
        {"name": "Write tests", "status": "todo"}
      ]
    }
  ]
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Project Alpha",
  "description": "Major feature implementation",
  "priority": "high",
  "due_date": "2026-03-01T00:00:00Z",
  "progress_percent": 25,
  "flow_chart": "graph TD; A[Start] --> B[Phase 1]; B --> C[Phase 2];",
  "context_tags": "backend,api,critical",
  "definition_of_done": "All phases complete, tests passing",
  "last_ai_summary": null,
  "last_ping": "2026-02-05T10:00:00Z",
  "created_at": "2026-02-05T10:00:00Z",
  "phases": [
    {
      "id": 1,
      "task_id": 1,
      "name": "Planning",
      "status": "completed",
      "order": 1,
      "todos": [
        {"id": 1, "phase_id": 1, "name": "Define requirements", "status": "done"},
        {"id": 2, "phase_id": 1, "name": "Create wireframes", "status": "done"}
      ]
    },
    {
      "id": 2,
      "task_id": 1,
      "name": "Development",
      "status": "in_progress",
      "order": 2,
      "todos": [
        {"id": 3, "phase_id": 2, "name": "Setup project", "status": "done"},
        {"id": 4, "phase_id": 2, "name": "Implement API", "status": "in_progress"},
        {"id": 5, "phase_id": 2, "name": "Write tests", "status": "todo"}
      ]
    }
  ],
  "comments": []
}
```

### 2.2 GET /tasks/{id} - Retrieve Task with Full Hierarchy

**Response:** Same structure as POST response, includes all nested phases, todos, and comments.

### 2.3 PATCH /todos/{id} - Update Todo Status

**Request Body:**
```json
{
  "status": "done"
}
```

**Behavior:**
- Updates todo status
- Triggers parent phase status recalculation
- Triggers task progress_percent recalculation
- Creates a system comment logging the change

### 2.4 PATCH /phases/{id} - Update Phase Status

**Request Body:**
```json
{
  "status": "completed"
}
```

**Behavior:**
- Updates phase status
- Updates all child todos if transitioning to completed
- Triggers task progress_percent recalculation
- Creates a system comment

### 2.5 POST /tasks/{id}/comments - Add Comment/Log Entry

**Request Body:**
```json
{
  "text": "Completed API implementation",
  "author": "agent"  // or "user", "system"
}
```

**Response:**
```json
{
  "id": 1,
  "task_id": 1,
  "text": "Completed API implementation",
  "author": "agent",
  "timestamp": "2026-02-05T10:30:00Z"
}
```

## Phase 3: Progress Calculation Logic

### 3.1 Automatic Progress Updates

```python
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
    phases = task.phases
    
    if not phases:
        return 0
    
    phase_weight = 100 / len(phases)
    total_progress = 0
    
    for phase in phases:
        if phase.status == "completed":
            total_progress += phase_weight
        elif phase.status == "in_progress":
            todos = phase.todos
            if todos:
                completed = sum(1 for t in todos if t.status == "done")
                total_progress += phase_weight * (completed / len(todos))
    
    return round(total_progress)
```

### 3.2 Status Propagation Rules

```python
PHASE_STATUS_RULES = {
    "not_started": "All todos are todo",
    "in_progress": "At least one todo is in_progress or done",
    "completed": "All todos are done",
    "blocked": "Manually set or dependency blocked"
}

TODO_STATUS_TRANSITIONS = {
    ("todo", "in_progress"): True,
    ("todo", "done"): True,  # Can skip in_progress
    ("in_progress", "done"): True,
    ("in_progress", "todo"): True,  # Can revert
    ("done", "in_progress"): True,
    ("done", "todo"): True
}
```

## Phase 4: Sub-Agent Authentication

### 4.1 Middleware Implementation

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")

def verify_sub_agent_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify that the request is from an authorized sub-agent.
    
    Sub-agents must provide the API_AUTH_TOKEN in the Authorization header
    as a Bearer token.
    """
    if not API_AUTH_TOKEN:
        raise HTTPException(
            status_code=500, 
            detail="API_AUTH_TOKEN not configured"
        )
    
    if credentials.credentials != API_AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials

# Endpoint with sub-agent auth
@app.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo_status(
    todo_id: int,
    update: TodoUpdate,
    session: Session = Depends(get_session),
    token: str = Depends(verify_sub_agent_token),  # Requires auth
):
    """Update todo status - requires sub-agent authentication."""
    ...
```

### 4.2 Sub-Agent API Client Example

```python
import os
import requests

API_BASE_URL = "http://localhost:8000"
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")

headers = {
    "Authorization": f"Bearer {API_AUTH_TOKEN}",
    "Content-Type": "application/json"
}

# Update todo status from sub-agent
response = requests.patch(
    f"{API_BASE_URL}/todos/1",
    json={"status": "done"},
    headers=headers
)
```

## Phase 5: Data Transfer Objects (DTOs)

### 5.1 Pydantic Schemas

```python
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

# Task Schemas
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str = "medium"
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
```

## Phase 6: Test Specifications

### 6.1 Test File Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_tasks.py                  # Task CRUD tests
├── test_phases.py                 # Phase tests
├── test_todos.py                  # Todo tests
├── test_comments.py               # Comment tests
├── test_nested_create.py          # Nested structure tests
├── test_progress_calculation.py   # Progress logic tests
├── test_auth.py                   # Authentication tests
└── test_integration.py            # End-to-end tests
```

### 6.2 Test Cases

#### CRUD Tests for Nested Structures

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| T-001 | test_create_task_with_phases | Create task with nested phases |
| T-002 | test_create_task_with_phases_and_todos | Full nested creation |
| T-003 | test_read_task_with_hierarchy | GET returns full nested data |
| T-004 | test_update_todo_status | PATCH /todos/{id} works |
| T-005 | test_update_todo_triggers_progress | Progress auto-calculated |
| T-006 | test_update_phase_status | PATCH /phases/{id} works |
| T-007 | test_create_comment | POST /tasks/{id}/comments works |
| T-008 | test_comments_included_in_task | Comments returned with task |

#### Status Update Propagation Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| P-001 | test_todo_done_updates_phase_progress | Phase progress updated |
| P-002 | test_all_todos_done_completes_phase | Phase auto-completes |
| P-003 | test_phase_completion_updates_task_progress | Task progress updated |
| P-004 | test_task_progress_calculation_accuracy | Math is correct |
| P-005 | test_system_comment_on_status_change | Auto-comment created |
| P-006 | test_blocked_phase_contributes_zero | Blocked phases handled |

#### Auth Verification Tests

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| A-001 | test_update_todo_without_token_fails | 401 without auth |
| A-002 | test_update_todo_with_invalid_token_fails | 401 with bad token |
| A-003 | test_update_todo_with_valid_token_succeeds | 200 with valid token |
| A-004 | test_phase_update_requires_auth | All mutations require auth |
| A-005 | test_comment_creation_requires_auth | Comments require auth |
| A-006 | test_read_operations_dont_require_auth | GET works without auth |

#### Edge Cases

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| E-001 | test_create_task_without_phases | Empty phases list |
| E-002 | test_create_phase_without_todos | Empty todos list |
| E-003 | test_progress_with_no_phases | Division by zero protection |
| E-004 | test_progress_with_no_todos | Empty phase handling |
| E-005 | test_invalid_status_values | Validation errors |
| E-006 | test_circular_references_prevented | No circular deps |

## Phase 7: Implementation Steps

### Step 1: Database Migration (1-2 hours)
- [ ] Update Task model with new fields
- [ ] Create Phase model
- [ ] Create Todo model
- [ ] Create Comment model
- [ ] Set up SQLModel relationships
- [ ] Run migration/create tables

### Step 2: API Endpoints (3-4 hours)
- [ ] Refactor POST /tasks/ for nested creation
- [ ] Update GET /tasks/{id} with eager loading
- [ ] Create PATCH /todos/{id}
- [ ] Create PATCH /phases/{id}
- [ ] Create POST /tasks/{id}/comments
- [ ] Implement progress calculation service

### Step 3: Authentication (1 hour)
- [ ] Verify existing auth middleware works
- [ ] Apply auth to mutation endpoints
- [ ] Update test fixtures with auth headers

### Step 4: Unit Tests (3-4 hours)
- [ ] Write CRUD tests for all models
- [ ] Write progress calculation tests
- [ ] Write auth verification tests
- [ ] Write nested structure tests
- [ ] Run full test suite

### Step 5: Integration (1 hour)
- [ ] End-to-end workflow test
- [ ] Verify sub-agent can update progress
- [ ] Performance check with large hierarchies

## Phase 8: Migration Strategy

### Backwards Compatibility

```python
# Migration path for existing tasks
# 1. Existing tasks become single-phase tasks
# 2. Create default phase for each existing task
# 3. Move task status to phase status

async def migrate_existing_tasks(session: Session):
    """Migrate existing flat tasks to new structure."""
    tasks = session.exec(select(Task)).all()
    
    for task in tasks:
        # Create a default phase for existing task
        phase = Phase(
            task_id=task.id,
            name="Default",
            status=task.status,
            order=1
        )
        session.add(phase)
        session.flush()  # Get phase.id
        
        # Create a todo representing the original task
        todo = Todo(
            phase_id=phase.id,
            name=task.name,
            status="done" if task.status == "done" else "todo"
        )
        session.add(todo)
    
    session.commit()
```

## Phase 9: API Documentation

### OpenAPI/Swagger

All endpoints will be automatically documented via FastAPI's OpenAPI generation. Key additions:

1. **Nested schemas** properly defined with Pydantic
2. **Authentication requirements** documented
3. **Example requests/responses** provided
4. **Error response schemas** defined

## Summary

**Total Estimated Time:** 10-12 hours

**Key Deliverables:**
1. Updated database schema with 4 related models
2. 5 API endpoints with nested support
3. Automatic progress calculation
4. Sub-agent authentication
5. Comprehensive test suite (30+ tests)
6. Migration script for existing data
7. Updated API documentation

**Risk Mitigation:**
- Backwards compatible migration path
- Extensive test coverage before deployment
- Clear separation between read (public) and write (auth) endpoints
