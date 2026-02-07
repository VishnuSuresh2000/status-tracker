# Ping System 2.0 Implementation Plan

## Overview
Full implementation plan for Ping System 2.0 with agent tracking, task assignment, acknowledgment API, snooze/reschedule capability, and escalation logic.

## Current System Analysis
- FastAPI backend with SQLite database
- SQLModel for ORM with Task, Phase, Todo, Comment models
- Basic notification system via worker.py
- HTML/JS frontend with Tailwind CSS
- Redis integration for background tasks

## Implementation Steps

### 1. Database Schema Changes

#### 1.1 Add Agent Model
**File: `main.py`** (add after Task model, line ~66)

```python
class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    type: str = Field(default="sub_agent")  # main_agent, sub_agent
    status: str = Field(default="idle")  # idle, busy, working, offline
    last_acknowledgment: Optional[datetime] = Field(default=None)
    current_task_id: Optional[int] = Field(foreign_key="tasks.id", default=None)
    capabilities: Optional[str] = Field(default=None)  # JSON array of skills
    endpoint_url: Optional[str] = Field(default=None)  # For agent communication
    timeout_minutes: int = Field(default=30)  # Custom timeout per agent
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    assignments: List["TaskAssignment"] = Relationship(back_populates="agent")
```

#### 1.2 Add TaskAssignment Model
**File: `main.py`** (add after Agent model, line ~90)

```python
class TaskAssignment(SQLModel, table=True):
    __tablename__ = "task_assignments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", index=True)
    agent_id: int = Field(foreign_key="agents.id", index=True)
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="pending")  # pending, acknowledged, snoozed, completed, failed
    original_agent_id: Optional[int] = Field(foreign_key="agents.id", default=None)  # For escalation tracking
    escalation_count: int = Field(default=0)
    snooze_until: Optional[datetime] = Field(default=None)
    last_ping_sent: Optional[datetime] = Field(default=None)
    
    # Relationships
    task: Task = Relationship(back_populates="assignments")
    agent: Agent = Relationship(back_populates="assignments")
```

#### 1.3 Update Task Model
**File: `main.py`** (modify Task model, line ~35-66)

Add these fields to Task class:
```python
# Add after existing fields around line 52
assigned_agent_id: Optional[int] = Field(foreign_key="agents.id", default=None)
ping_interval_minutes: int = Field(default=30)  # Specific ping interval
is_ping_enabled: bool = Field(default=True)
last_agent_acknowledgment: Optional[datetime] = Field(default=None)

# Add to relationships around line 65
assignments: List["TaskAssignment"] = Relationship(
    back_populates="task", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
)
```

### 2. Database Migration

#### 2.1 Create Migration Script
**New File: `migrate_agent_system.py`**

```python
#!/usr/bin/env python3
"""
Migration script for Ping System 2.0
Adds Agent and TaskAssignment tables, updates Task table
"""
from sqlmodel import SQLModel, create_engine, Session, text
from main import Agent, TaskAssignment, Task
from datetime import datetime, timezone
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tasks.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def migrate():
    print("Starting migration for Ping System 2.0...")
    
    with Session(engine) as session:
        # Create new tables
        SQLModel.metadata.create_all(engine)
        
        # Create default Ruto agent
        ruto = Agent(
            name="Ruto",
            type="main_agent",
            status="idle",
            capabilities="task_management,escalation,coordination",
            timeout_minutes=60
        )
        session.add(ruto)
        
        # Add new columns to existing tasks table
        try:
            session.exec(text("""
                ALTER TABLE tasks ADD COLUMN assigned_agent_id INTEGER REFERENCES agents(id)
            """))
            print("Added assigned_agent_id column to tasks")
        except Exception as e:
            print(f"assigned_agent_id column may already exist: {e}")
            
        try:
            session.exec(text("""
                ALTER TABLE tasks ADD COLUMN ping_interval_minutes INTEGER DEFAULT 30
            """))
            print("Added ping_interval_minutes column to tasks")
        except Exception as e:
            print(f"ping_interval_minutes column may already exist: {e}")
            
        try:
            session.exec(text("""
                ALTER TABLE tasks ADD COLUMN is_ping_enabled BOOLEAN DEFAULT 1
            """))
            print("Added is_ping_enabled column to tasks")
        except Exception as e:
            print(f"is_ping_enabled column may already exist: {e}")
            
        try:
            session.exec(text("""
                ALTER TABLE tasks ADD COLUMN last_agent_acknowledgment DATETIME
            """))
            print("Added last_agent_acknowledgment column to tasks")
        except Exception as e:
            print(f"last_agent_acknowledgment column may already exist: {e}")
        
        session.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
```

### 3. API Endpoints

#### 3.1 Agent Management Endpoints
**File: `main.py`** (add after existing endpoints, line ~825)

```python
# Agent Management Endpoints
@app.post("/agents/", response_model=dict)
def create_agent(
    name: str,
    agent_type: str = "sub_agent",
    capabilities: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    timeout_minutes: int = 30,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Create a new agent."""
    existing_agent = session.exec(select(Agent).where(Agent.name == name)).first()
    if existing_agent:
        raise HTTPException(status_code=400, detail="Agent already exists")
    
    agent = Agent(
        name=name,
        type=agent_type,
        capabilities=capabilities,
        endpoint_url=endpoint_url,
        timeout_minutes=timeout_minutes,
        status="idle"
    )
    session.add(agent)
    session.commit()
    return {"message": f"Agent '{name}' created successfully", "agent_id": agent.id}

@app.get("/agents/", response_model=List[dict])
def get_agents(session: Session = Depends(get_session)):
    """Get all agents with current status."""
    agents = session.exec(select(Agent).where(Agent.is_active == True)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "status": a.status,
            "last_acknowledgment": a.last_acknowledgment,
            "current_task_id": a.current_task_id,
            "capabilities": a.capabilities,
            "timeout_minutes": a.timeout_minutes
        }
        for a in agents
    ]

@app.post("/agents/{agent_id}/acknowledge", response_model=dict)
def acknowledge_task(
    agent_id: int,
    task_id: int,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Agent acknowledges a task assignment."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Find the assignment
    assignment = session.exec(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.agent_id == agent_id,
            TaskAssignment.status.in_(["pending", "snoozed"])
        )
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="No pending assignment found")
    
    # Update assignment and agent
    assignment.status = "acknowledged"
    assignment.acknowledged_at = datetime.now(timezone.utc)
    agent.status = "working"
    agent.last_acknowledgment = datetime.now(timezone.utc)
    agent.current_task_id = task_id
    task.last_agent_acknowledgment = datetime.now(timezone.utc)
    
    session.add_all([assignment, agent, task])
    session.commit()
    
    create_system_comment(task_id, f"Agent '{agent.name}' acknowledged task", session)
    
    return {
        "message": f"Task acknowledged by {agent.name}",
        "acknowledged_at": assignment.acknowledged_at
    }

@app.post("/agents/{agent_id}/snooze", response_model=dict)
def snooze_task(
    agent_id: int,
    task_id: int,
    minutes: int = 30,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Agent snoozes a task assignment."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    assignment = session.exec(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.agent_id == agent_id,
            TaskAssignment.status == "pending"
        )
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="No pending assignment found")
    
    assignment.status = "snoozed"
    assignment.snooze_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    session.add(assignment)
    session.commit()
    
    create_system_comment(task_id, f"Agent '{agent.name}' snoozed task for {minutes} minutes", session)
    
    return {
        "message": f"Task snoozed by {agent.name} for {minutes} minutes",
        "snooze_until": assignment.snooze_until
    }
```

#### 3.2 Task Assignment Endpoints
**File: `main.py`** (add after agent endpoints)

```python
@app.post("/tasks/{task_id}/assign", response_model=dict)
def assign_task(
    task_id: int,
    agent_name: Optional[str] = None,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token),
):
    """Assign task to an agent (auto-assign if no agent specified)."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Find target agent
    if agent_name:
        agent = session.exec(select(Agent).where(Agent.name == agent_name, Agent.is_active == True)).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        # Auto-assign to least busy sub-agent
        agent = session.exec(
            select(Agent).where(
                Agent.type == "sub_agent",
                Agent.is_active == True,
                Agent.status.in_(["idle", "working"])
            ).order_by(Agent.last_acknowledgment.asc().nullsfirst())
        ).first()
        
        if not agent:
            agent = session.exec(
                select(Agent).where(Agent.name == "Ruto", Agent.is_active == True)
            ).first()
    
    if not agent:
        raise HTTPException(status_code=500, detail="No available agents found")
    
    # Create assignment
    assignment = TaskAssignment(
        task_id=task_id,
        agent_id=agent.id,
        status="pending"
    )
    
    task.assigned_agent_id = agent.id
    agent.current_task_id = task_id
    agent.status = "busy"
    
    session.add_all([assignment, task, agent])
    session.commit()
    
    create_system_comment(task_id, f"Task assigned to agent '{agent.name}'", session)
    
    return {
        "message": f"Task assigned to {agent.name}",
        "agent": agent.name,
        "assignment_id": assignment.id
    }

@app.get("/tasks/{task_id}/assignments", response_model=List[dict])
def get_task_assignments(
    task_id: int,
    session: Session = Depends(get_session)
):
    """Get assignment history for a task."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    assignments = session.exec(
        select(TaskAssignment).where(TaskAssignment.task_id == task_id)
        .order_by(TaskAssignment.assigned_at.desc())
    ).all()
    
    return [
        {
            "id": a.id,
            "agent_name": a.agent.name if a.agent else "Unknown",
            "assigned_at": a.assigned_at,
            "acknowledged_at": a.acknowledged_at,
            "status": a.status,
            "escalation_count": a.escalation_count,
            "snooze_until": a.snooze_until
        }
        for a in assignments
    ]
```

### 4. Enhanced Worker System

#### 4.1 Update Worker for Agent Pings
**File: `worker.py`** (complete rewrite)

```python
import time
import os
import requests
from sqlmodel import Session, create_engine, select
from main import Task, Agent, TaskAssignment
from datetime import datetime, timezone, timedelta
from notifications import send_task_reminder
import json

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tasks.db")
engine = create_engine(DATABASE_URL)

class PingWorker:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
    def send_ping_to_agent(self, agent: Agent, task: Task, session: Session) -> bool:
        """Send ping to agent endpoint."""
        if not agent.endpoint_url:
            print(f"[WARNING] Agent {agent.name} has no endpoint URL")
            return False
            
        try:
            payload = {
                "task_id": task.id,
                "task_name": task.name,
                "ping_time": datetime.now(timezone.utc).isoformat(),
                "timeout_minutes": agent.timeout_minutes
            }
            
            response = requests.post(
                f"{agent.endpoint_url}/ping",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[PING] Successfully pinged {agent.name} for task {task.name}")
                return True
            else:
                print(f"[ERROR] Failed to ping {agent.name}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Exception pinging {agent.name}: {str(e)}")
            return False
    
    def check_and_ping_agents(self):
        """Main ping loop with agent logic."""
        try:
            with Session(engine) as session:
                now = datetime.now(timezone.utc)
                
                # Get all active tasks that need pinging
                statement = select(Task).where(
                    Task.is_ping_enabled == True,
                    Task.status.in_(["todo", "in_progress"])
                )
                tasks = session.exec(statement).all()
                
                for task in tasks:
                    if task.id is None:
                        continue
                        
                    # Get current assignment
                    assignment = session.exec(
                        select(TaskAssignment).where(
                            TaskAssignment.task_id == task.id,
                            TaskAssignment.status.in_(["pending", "acknowledged", "snoozed"])
                        ).order_by(TaskAssignment.assigned_at.desc())
                    ).first()
                    
                    if not assignment:
                        # Create initial assignment
                        self.auto_assign_task(task, session)
                        continue
                    
                    agent = session.get(Agent, assignment.agent_id) if assignment.agent_id else None
                    if not agent:
                        continue
                    
                    # Check if ping is needed
                    ping_interval = timedelta(minutes=task.ping_interval_minutes)
                    should_ping = False
                    
                    if assignment.status == "pending":
                        # First ping or timeout
                        if not assignment.last_ping_sent:
                            should_ping = True
                        elif now > assignment.last_ping_sent + ping_interval:
                            should_ping = True
                    
                    elif assignment.status == "acknowledged":
                        # Check if agent is overdue for acknowledgment
                        if agent.last_acknowledgment:
                            timeout = timedelta(minutes=agent.timeout_minutes)
                            if now > agent.last_acknowledgment + timeout:
                                should_ping = True
                                # Trigger escalation if needed
                                self.handle_timeout(task, agent, assignment, session)
                    
                    elif assignment.status == "snoozed":
                        # Check if snooze period is over
                        if assignment.snooze_until and now > assignment.snooze_until:
                            assignment.status = "pending"
                            session.add(assignment)
                            should_ping = True
                    
                    if should_ping:
                        if self.send_ping_to_agent(agent, task, session):
                            assignment.last_ping_sent = now
                            session.add(assignment)
                            
                            # Update task's last_ping for UI
                            task.last_ping = now
                            session.add(task)
                
                session.commit()
                
        except Exception as e:
            print(f"[ERROR] Worker loop error: {e}")
    
    def auto_assign_task(self, task: Task, session: Session):
        """Auto-assign task to available agent."""
        # Try sub-agents first
        agent = session.exec(
            select(Agent).where(
                Agent.type == "sub_agent",
                Agent.is_active == True,
                Agent.status.in_(["idle", "working"])
            ).order_by(Agent.last_acknowledgment.asc().nullsfirst())
        ).first()
        
        # Fall back to Ruto if no sub-agents available
        if not agent:
            agent = session.exec(
                select(Agent).where(Agent.name == "Ruto", Agent.is_active == True)
            ).first()
        
        if agent:
            assignment = TaskAssignment(
                task_id=task.id,
                agent_id=agent.id,
                status="pending"
            )
            task.assigned_agent_id = agent.id
            agent.current_task_id = task.id
            agent.status = "busy"
            
            session.add_all([assignment, task, agent])
            print(f"[ASSIGN] Auto-assigned task '{task.name}' to {agent.name}")
    
    def handle_timeout(self, task: Task, agent: Agent, assignment: TaskAssignment, session: Session):
        """Handle agent timeout and escalation."""
        if agent.type == "sub_agent":
            # Escalate to Ruto
            ruto = session.exec(select(Agent).where(Agent.name == "Ruto", Agent.is_active == True)).first()
            if ruto:
                # Create new assignment to Ruto
                escalation_assignment = TaskAssignment(
                    task_id=task.id,
                    agent_id=ruto.id,
                    status="pending",
                    original_agent_id=agent.id,
                    escalation_count=assignment.escalation_count + 1
                )
                
                # Update previous assignment
                assignment.status = "failed"
                
                # Update agent status
                agent.status = "idle"
                agent.current_task_id = None
                
                # Update task and Ruto
                task.assigned_agent_id = ruto.id
                ruto.current_task_id = task.id
                ruto.status = "busy"
                
                session.add_all([escalation_assignment, assignment, agent, task, ruto])
                
                create_system_comment(
                    task.id, 
                    f"Escalated from {agent.name} (timeout) to {ruto.name} (attempt {escalation_assignment.escalation_count})", 
                    session
                )
                
                print(f"[ESCALATION] Task '{task.name}' escalated from {agent.name} to {ruto.name}")
        else:
            # Ruto timeout - just note it, keep pinging
            create_system_comment(
                task.id,
                f"Main agent {agent.name} timeout - continuing to ping",
                session
            )
            print(f"[TIMEOUT] Main agent {agent.name} timeout for task '{task.name}'")

def worker():
    print("[WORKER] Enhanced ping worker started...")
    print("[WORKER] Checking for agent pings every 30 seconds")
    
    ping_worker = PingWorker()
    
    while True:
        ping_worker.check_and_ping_agents()
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    worker()
```

### 5. UI Enhancements

#### 5.1 Agent Ping Back Section
**File: `index.html`** (add after task columns, line ~76)

```html
<!-- Agent Status Section -->
<div class="mt-8 bg-white p-4 md:p-6 rounded-lg shadow-md border-t-4 border-purple-600">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Agent Ping Back
    </h2>
    <div id="agentStatusList" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Agent cards will be populated here -->
    </div>
</div>
```

#### 5.2 Agent Card Component
**File: `index.html`** (add to JavaScript section, after createTaskCard function)

```javascript
function createAgentCard(agent) {
    const div = document.createElement('div');
    div.className = `border rounded-lg p-4 ${agent.type === 'main_agent' ? 'border-purple-300 bg-purple-50' : 'border-blue-300 bg-blue-50'}`;
    
    const statusColors = {
        'idle': 'bg-green-100 text-green-700',
        'busy': 'bg-yellow-100 text-yellow-700', 
        'working': 'bg-blue-100 text-blue-700',
        'offline': 'bg-gray-100 text-gray-700'
    };
    
    const statusColor = statusColors[agent.status] || statusColors.offline;
    const lastAck = agent.last_acknowledgment ? 
        `<span class="text-xs text-gray-500">Last ack: ${new Date(agent.last_acknowledgment).toLocaleString()}</span>` :
        '<span class="text-xs text-gray-400">Never acknowledged</span>';
    
    div.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div>
                <h4 class="font-bold text-gray-800">${agent.name}</h4>
                <span class="text-xs uppercase font-bold px-2 py-0.5 rounded-full ${statusColor}">${agent.status}</span>
                ${agent.type === 'main_agent' ? '<span class="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full ml-1">MAIN</span>' : ''}
            </div>
            ${agent.current_task_id ? `<span class="text-xs bg-blue-500 text-white px-2 py-1 rounded">Task #${agent.current_task_id}</span>` : ''}
        </div>
        
        ${agent.capabilities ? `
        <div class="mb-2">
            <p class="text-xs text-gray-600 mb-1">Capabilities:</p>
            <div class="flex flex-wrap gap-1">
                ${agent.capabilities.split(',').map(cap => `<span class="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded">${cap.trim()}</span>`).join('')}
            </div>
        </div>
        ` : ''}
        
        <div class="text-xs text-gray-500">
            <p>Timeout: ${agent.timeout_minutes}min</p>
            ${lastAck}
        </div>
    `;
    
    return div;
}

async function fetchAgentStatus() {
    try {
        const response = await fetch('/agents/');
        const agents = await response.json();
        
        const container = document.getElementById('agentStatusList');
        container.innerHTML = '';
        
        agents.forEach(agent => {
            const card = createAgentCard(agent);
            container.appendChild(card);
        });
        
    } catch (e) {
        console.error("Failed to fetch agent status:", e);
    }
}
```

#### 5.3 Update Initial Fetch
**File: `index.html`** (modify the initialization section, line ~592)

```javascript
// Initial fetch
fetchTasks();
fetchNotifications();
fetchAgentStatus();

// Refresh intervals
setInterval(fetchTasks, 30000);
setInterval(fetchNotifications, 30000);
setInterval(fetchAgentStatus, 30000);
```

#### 5.4 Task Assignment UI
**File: `index.html`** (add to modal action buttons section, line ~121)

```javascript
// Add assignment controls in task details modal
// In the openTaskDetails function, after the action button logic (line ~375):

// Assignment Controls
if (task.assigned_agent_id) {
    const agentInfo = agents.find(a => a.id === task.assigned_agent_id);
    if (agentInfo) {
        const assignmentDiv = document.createElement('div');
        assignmentDiv.className = 'mt-4 p-3 bg-blue-50 rounded border border-blue-200';
        assignmentDiv.innerHTML = `
            <div class="flex justify-between items-center">
                <span class="text-sm font-medium text-blue-800">
                    Assigned to: ${agentInfo.name} (${agentInfo.status})
                </span>
                <button onclick="reassignTask(${task.id})" class="text-xs text-blue-600 hover:text-blue-800 hover:underline">
                    Reassign
                </button>
            </div>
        `;
        document.getElementById('modalTaskMeta').appendChild(assignmentDiv);
    }
}

// Add reassignTask function
async function reassignTask(taskId) {
    const agentName = prompt("Enter agent name (leave blank for auto-assign):");
    if (agentName === null) return; // User cancelled
    
    try {
        await fetch(`/tasks/${taskId}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_name: agentName || null })
        });
        openTaskDetails(taskId); // Refresh modal
        fetchTasks();
        fetchAgentStatus();
    } catch (e) {
        console.error("Reassign failed:", e);
    }
}
```

### 6. Pydantic Schemas

#### 6.1 Agent Schemas
**File: `main.py`** (add after existing schemas, line ~213)

```python
# Agent Schemas
class AgentBase(BaseModel):
    name: str
    type: str = "sub_agent"
    capabilities: Optional[str] = None
    endpoint_url: Optional[str] = None
    timeout_minutes: int = 30

class AgentCreate(AgentBase):
    pass

class AgentRead(AgentBase):
    id: int
    status: str
    last_acknowledgment: Optional[datetime]
    current_task_id: Optional[int]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Assignment Schemas  
class AssignmentBase(BaseModel):
    task_id: int
    agent_id: int

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentRead(AssignmentBase):
    id: int
    assigned_at: datetime
    acknowledged_at: Optional[datetime]
    status: str
    escalation_count: int
    snooze_until: Optional[datetime]
    last_ping_sent: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
```

### 7. Test Cases

#### 7.1 Agent System Tests
**New File: `tests/test_agent_system.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
from main import app, Agent, Task, TaskAssignment
from datetime import datetime, timezone, timedelta

client = TestClient(app)
DATABASE_URL = "sqlite:///./test_tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture
def session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def auth_token():
    return os.getenv("API_AUTH_TOKEN", "test-token")

class TestAgentSystem:
    def test_create_agent(self, session, auth_token):
        response = client.post(
            "/agents/",
            params={"name": "test-agent", "capabilities": "coding,testing"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Agent 'test-agent' created successfully"
        
    def test_get_agents(self, session, auth_token):
        # Create test agent
        agent = Agent(name="test-agent", type="sub_agent", capabilities="coding")
        session.add(agent)
        session.commit()
        
        response = client.get("/agents/")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 1
        assert agents[0]["name"] == "test-agent"
        
    def test_task_assignment(self, session, auth_token):
        # Create task and agent
        task = Task(name="Test Task", status="todo")
        agent = Agent(name="test-agent", type="sub_agent")
        session.add_all([task, agent])
        session.commit()
        
        response = client.post(
            f"/tasks/{task.id}/assign",
            params={"agent_name": "test-agent"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "test-agent"
        
    def test_agent_acknowledgment(self, session, auth_token):
        # Create task, agent, and assignment
        task = Task(name="Test Task", status="todo")
        agent = Agent(name="test-agent", type="sub_agent")
        session.add_all([task, agent])
        session.commit()
        
        # Create assignment
        assignment = TaskAssignment(task_id=task.id, agent_id=agent.id)
        session.add(assignment)
        session.commit()
        
        response = client.post(
            f"/agents/{agent.id}/acknowledge",
            params={"task_id": task.id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "acknowledged_at" in data
        
    def test_task_reassignment_history(self, session, auth_token):
        # Create task and agents
        task = Task(name="Test Task", status="todo")
        agent1 = Agent(name="agent1", type="sub_agent")
        agent2 = Agent(name="agent2", type="sub_agent")
        session.add_all([task, agent1, agent2])
        session.commit()
        
        # First assignment
        client.post(
            f"/tasks/{task.id}/assign",
            params={"agent_name": "agent1"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Reassignment
        client.post(
            f"/tasks/{task.id}/assign",
            params={"agent_name": "agent2"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        response = client.get(f"/tasks/{task.id}/assignments")
        assert response.status_code == 200
        assignments = response.json()
        assert len(assignments) == 2
```

#### 7.2 Worker System Tests
**New File: `tests/test_ping_worker.py`**

```python
import pytest
from unittest.mock import Mock, patch
from worker import PingWorker
from main import Agent, Task, TaskAssignment
from datetime import datetime, timezone, timedelta

class TestPingWorker:
    @pytest.fixture
    def ping_worker(self):
        return PingWorker()
    
    def test_auto_assign_task(self, ping_worker, session):
        # Create test task and agents
        task = Task(name="Test Task", status="todo")
        sub_agent = Agent(name="sub-agent", type="sub_agent", status="idle")
        main_agent = Agent(name="Ruto", type="main_agent", status="idle")
        session.add_all([task, sub_agent, main_agent])
        session.commit()
        
        ping_worker.auto_assign_task(task, session)
        
        # Should assign to sub-agent first
        assert task.assigned_agent_id == sub_agent.id
        assert sub_agent.status == "busy"
        assert sub_agent.current_task_id == task.id
        
    def test_escalation_to_main_agent(self, ping_worker, session):
        # Create test task and agents
        task = Task(name="Test Task", status="todo")
        sub_agent = Agent(name="sub-agent", type="sub_agent", status="working")
        main_agent = Agent(name="Ruto", type="main_agent", status="idle")
        
        # Create existing assignment that failed
        assignment = TaskAssignment(
            task_id=task.id,
            agent_id=sub_agent.id,
            status="pending"
        )
        
        session.add_all([task, sub_agent, main_agent, assignment])
        session.commit()
        
        # Simulate timeout
        sub_agent.last_acknowledgment = datetime.now(timezone.utc) - timedelta(minutes=35)
        session.add(sub_agent)
        session.commit()
        
        ping_worker.handle_timeout(task, sub_agent, assignment, session)
        
        # Should escalate to main agent
        updated_assignment = session.get(TaskAssignment, assignment.id)
        assert updated_assignment.status == "failed"
        assert task.assigned_agent_id == main_agent.id
        assert main_agent.status == "busy"
        
    @patch('requests.post')
    def test_send_ping_to_agent_success(self, mock_post, ping_worker, session):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        agent = Agent(name="test-agent", endpoint_url="http://localhost:9000")
        task = Task(name="Test Task")
        session.add_all([agent, task])
        session.commit()
        
        result = ping_worker.send_ping_to_agent(agent, task, session)
        assert result is True
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_send_ping_to_agent_failure(self, mock_post, ping_worker, session):
        # Setup mock to raise exception
        mock_post.side_effect = Exception("Network error")
        
        agent = Agent(name="test-agent", endpoint_url="http://localhost:9000")
        task = Task(name="Test Task")
        session.add_all([agent, task])
        session.commit()
        
        result = ping_worker.send_ping_to_agent(agent, task, session)
        assert result is False
```

### 8. Configuration Files

#### 8.1 Environment Variables
**File: `.env.example`** (update existing file)

```bash
# Database
DATABASE_URL=sqlite:///./data/tasks.db

# Authentication
API_AUTH_TOKEN=your-secure-token-here

# Redis
REDIS_HOST=localhost

# API Configuration (for agent communication)
API_BASE_URL=http://localhost:8000

# Worker Configuration
WORKER_INTERVAL_SECONDS=30
DEFAULT_PING_INTERVAL_MINUTES=30
DEFAULT_AGENT_TIMEOUT_MINUTES=30

# Agent Configuration
RUTO_TIMEOUT_MINUTES=60
SUB_AGENT_TIMEOUT_MINUTES=30
MAX_ESCALATION_ATTEMPTS=3
```

### 9. Deployment Steps

#### 9.1 Migration Checklist
1. Backup existing database
2. Run migration script: `python migrate_agent_system.py`
3. Verify new tables exist: `sqlite3 ./data/tasks.db ".schema agents"`
4. Test basic functionality

#### 9.2 Service Updates
1. Update worker process: `python worker.py` (enhanced version)
2. Restart main application: `uvicorn main:app --reload`
3. Verify agent endpoints are accessible
4. Test agent registration and task assignment

#### 9.3 Monitoring Setup
1. Monitor agent status endpoints
2. Set up alerts for escalation failures
3. Track ping success rates
4. Monitor agent response times

### 10. Testing Strategy

#### 10.1 Unit Tests
- Agent creation and management
- Task assignment logic
- Ping worker functionality
- Escalation mechanisms
- Database migrations

#### 10.2 Integration Tests
- End-to-end agent task flow
- API authentication and authorization
- Worker-agent communication
- Database transaction integrity
- UI interaction with new endpoints

#### 10.3 Performance Tests
- Multiple concurrent agents
- High-volume task assignments
- Worker process under load
- Database query optimization
- Response time benchmarks

### 11. Security Considerations

#### 11.1 API Security
- All agent endpoints require authentication
- Agent endpoint URL validation
- Rate limiting for ping requests
- Secure token management

#### 11.2 Data Security
- Agent capability verification
- Task assignment authorization
- Audit logging for all assignments
- Sensitive data protection

### 12. Rollback Plan

#### 12.1 Database Rollback
```sql
-- Manual rollback SQL if needed
DROP TABLE IF EXISTS task_assignments;
DROP TABLE IF EXISTS agents;

-- Remove columns from tasks
ALTER TABLE tasks DROP COLUMN assigned_agent_id;
ALTER TABLE tasks DROP COLUMN ping_interval_minutes;
ALTER TABLE tasks DROP COLUMN is_ping_enabled;
ALTER TABLE tasks DROP COLUMN last_agent_acknowledgment;
```

#### 12.2 Code Rollback
1. Revert to previous versions of main.py and worker.py
2. Restore original index.html
3. Remove new agent-specific endpoints
4. Restart services with legacy configuration

### 13. Timeline Estimate

- **Phase 1 (Database & Models)**: 2-3 days
- **Phase 2 (API Endpoints)**: 3-4 days  
- **Phase 3 (Worker System)**: 3-4 days
- **Phase 4 (UI Updates)**: 2-3 days
- **Phase 5 (Testing & Integration)**: 4-5 days
- **Phase 6 (Deployment)**: 1-2 days

**Total Estimated Time: 15-21 days**

### 14. Success Metrics

- Agent acknowledgment rate > 95%
- Average response time < 5 minutes
- Escalation success rate > 90%
- System uptime > 99.5%
- Zero data loss during migration

This comprehensive plan covers all aspects of implementing Ping System 2.0 with agent tracking, from database changes through deployment and monitoring.