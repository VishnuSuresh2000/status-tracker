"""Unit tests for Ping System 2.0 - Agent and Task Assignment models and endpoints."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool, select
from datetime import datetime, timezone, timedelta
from main import (
    app,
    get_session,
    Agent,
    TaskAssignment,
    Task,
    AgentCreate,
    AgentRead,
    TaskAssignmentCreate,
    TaskAssignmentRead,
)

# Setup in-memory SQLite for testing
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture():
    """Return valid authentication headers for protected endpoints."""
    return {"Authorization": "Bearer test-auth-token-for-tests"}


@pytest.fixture(name="sample_agent")
def sample_agent_fixture(session: Session):
    """Create a sample agent for testing."""
    agent = Agent(
        name="Test Agent",
        type="sub_agent",
        capabilities="testing,debugging",
        endpoint_url="https://example.com/webhook",
        timeout_minutes=30,
        is_active=True,
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@pytest.fixture(name="sample_task")
def sample_task_fixture(session: Session):
    """Create a sample task for testing."""
    task = Task(
        name="Test Task",
        description="Test task description",
        priority="high",
        ping_interval_minutes=30,
        is_ping_enabled=True,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# ============================================================================
# TEST AGENT MODEL
# ============================================================================


class TestAgentModel:
    """Test suite for Agent model."""

    def test_create_agent(self, session: Session):
        """Test creating an agent with all fields."""
        agent = Agent(
            name="Full Test Agent",
            type="main_agent",
            status="idle",
            capabilities="full_stack,testing",
            endpoint_url="https://agent.example.com",
            timeout_minutes=45,
            is_active=True,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

        assert agent.id is not None
        assert agent.name == "Full Test Agent"
        assert agent.type == "main_agent"
        assert agent.status == "idle"
        assert agent.capabilities == "full_stack,testing"
        assert agent.endpoint_url == "https://agent.example.com"
        assert agent.timeout_minutes == 45
        assert agent.is_active is True
        assert agent.created_at is not None

    def test_agent_default_values(self, session: Session):
        """Test agent default field values."""
        agent = Agent(name="Default Agent")
        session.add(agent)
        session.commit()
        session.refresh(agent)

        assert agent.type == "sub_agent"
        assert agent.status == "idle"
        assert agent.timeout_minutes == 30
        assert agent.is_active is True
        assert agent.last_acknowledgment is None

    def test_agent_status_update(self, session: Session, sample_agent):
        """Test updating agent status and acknowledgment."""
        original_time = sample_agent.last_acknowledgment

        # Update status and acknowledgment
        sample_agent.status = "working"
        sample_agent.last_acknowledgment = datetime.now(timezone.utc)
        session.add(sample_agent)
        session.commit()
        session.refresh(sample_agent)

        assert sample_agent.status == "working"
        assert sample_agent.last_acknowledgment != original_time


# ============================================================================
# TEST TASK ASSIGNMENT MODEL
# ============================================================================


class TestTaskAssignmentModel:
    """Test suite for TaskAssignment model."""

    def test_create_task_assignment(self, session: Session, sample_task, sample_agent):
        """Test creating a task assignment."""
        assignment = TaskAssignment(
            task_id=sample_task.id, agent_id=sample_agent.id, status="pending"
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.id is not None
        assert assignment.task_id == sample_task.id
        assert assignment.agent_id == sample_agent.id
        assert assignment.status == "pending"
        assert assignment.assigned_at is not None
        assert assignment.acknowledged_at is None
        assert assignment.escalation_count == 0
        assert assignment.snooze_until is None
        assert assignment.last_ping_sent is None

    def test_assignment_status_tracking(
        self, session: Session, sample_task, sample_agent
    ):
        """Test tracking assignment status changes."""
        assignment = TaskAssignment(
            task_id=sample_task.id, agent_id=sample_agent.id, status="pending"
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        # Update to acknowledged
        assignment.status = "acknowledged"
        assignment.acknowledged_at = datetime.now(timezone.utc)
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.status == "acknowledged"
        assert assignment.acknowledged_at is not None

        # Update to completed
        assignment.status = "completed"
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.status == "completed"

    def test_escalation_count(self, session: Session, sample_task, sample_agent):
        """Test escalation count tracking."""
        assignment = TaskAssignment(
            task_id=sample_task.id,
            agent_id=sample_agent.id,
            status="pending",
            escalation_count=0,
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.escalation_count == 0

        # Increment escalation count
        assignment.escalation_count += 1
        session.add(assignment)
        session.commit()
        session.refresh(assignment)

        assert assignment.escalation_count == 1


# ============================================================================
# TEST AGENT ENDPOINTS
# ============================================================================


class TestAgentEndpoints:
    """Test suite for Agent endpoints."""

    def test_create_agent_endpoint(self, client: TestClient, auth_headers: dict):
        """Test POST /agents/ endpoint."""
        agent_data = {
            "name": "API Test Agent",
            "type": "sub_agent",
            "capabilities": "api_testing,validation",
            "endpoint_url": "https://api-test.example.com",
            "timeout_minutes": 25,
            "is_active": True,
        }
        response = client.post("/agents/", json=agent_data, headers=auth_headers)
        data = response.json()

        assert response.status_code == 200
        assert data["name"] == "API Test Agent"
        assert data["type"] == "sub_agent"
        assert data["capabilities"] == "api_testing,validation"
        assert data["endpoint_url"] == "https://api-test.example.com"
        assert data["timeout_minutes"] == 25
        assert data["is_active"] is True
        assert data["status"] == "idle"  # Default value
        assert "id" in data
        assert "created_at" in data

    def test_create_agent_endpoint_requires_auth(self, client: TestClient):
        """Test that POST /agents/ requires authentication."""
        agent_data = {"name": "No Auth Agent"}
        response = client.post("/agents/", json=agent_data)
        assert response.status_code == 401

    def test_list_agents(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test GET /agents/ endpoint."""
        # Create multiple agents
        agents = [
            Agent(name="Agent 1", type="main_agent"),
            Agent(name="Agent 2", type="sub_agent"),
            Agent(name="Agent 3", type="sub_agent", is_active=False),
        ]
        for agent in agents:
            session.add(agent)
        session.commit()

        response = client.get("/agents/", headers=auth_headers)
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 3
        assert any(agent["name"] == "Agent 1" for agent in data)
        assert any(agent["name"] == "Agent 2" for agent in data)
        assert any(agent["name"] == "Agent 3" for agent in data)

    def test_list_agents_no_auth_required(self, client: TestClient, session: Session):
        """Test that GET /agents/ doesn't require authentication."""
        # Create an agent
        agent = Agent(name="Public Agent")
        session.add(agent)
        session.commit()

        response = client.get("/agents/")
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["name"] == "Public Agent"

    def test_get_single_agent(
        self, client: TestClient, sample_agent, auth_headers: dict
    ):
        """Test GET /agents/{id} endpoint."""
        response = client.get(f"/agents/{sample_agent.id}", headers=auth_headers)
        data = response.json()

        assert response.status_code == 200
        assert data["id"] == sample_agent.id
        assert data["name"] == sample_agent.name
        assert data["type"] == sample_agent.type
        assert data["status"] == sample_agent.status

    def test_get_single_agent_not_found(self, client: TestClient, auth_headers: dict):
        """Test GET /agents/{id} with non-existent ID."""
        response = client.get("/agents/999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_agent_acknowledge(
        self, client: TestClient, sample_agent, auth_headers: dict
    ):
        """Test POST /agents/{id}/acknowledge endpoint."""
        original_ack_time = sample_agent.last_acknowledgment
        original_status = sample_agent.status

        response = client.post(
            f"/agents/{sample_agent.id}/acknowledge", headers=auth_headers
        )
        data = response.json()

        assert response.status_code == 200
        assert data["message"] == "Agent acknowledged successfully"
        assert data["agent_id"] == sample_agent.id
        assert "last_acknowledgment" in data

        # Verify the agent was updated
        assert data["last_acknowledgment"] != original_ack_time

    def test_agent_acknowledge_not_found(self, client: TestClient, auth_headers: dict):
        """Test POST /agents/{id}/acknowledge with non-existent agent."""
        response = client.post("/agents/999/acknowledge", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_agent_acknowledge_requires_auth(self, client: TestClient, sample_agent):
        """Test that POST /agents/{id}/acknowledge requires authentication."""
        response = client.post(f"/agents/{sample_agent.id}/acknowledge")
        assert response.status_code == 401

    def test_agent_snooze(self, client: TestClient, sample_agent, auth_headers: dict):
        """Test POST /agents/{id}/snooze endpoint."""
        snooze_minutes = 15
        response = client.post(
            f"/agents/{sample_agent.id}/snooze?snooze_minutes={snooze_minutes}",
            headers=auth_headers,
        )
        data = response.json()

        assert response.status_code == 200
        assert data["message"] == "Agent snoozed successfully"
        assert data["agent_id"] == sample_agent.id
        assert "snooze_until" in data

        # Verify snooze time is in the future
        snooze_until = datetime.fromisoformat(
            data["snooze_until"].replace("Z", "+00:00")
        )
        expected_time = datetime.now(timezone.utc) + timedelta(minutes=snooze_minutes)
        # Allow for small time differences (within 1 minute)
        time_diff = abs((snooze_until - expected_time).total_seconds())
        assert time_diff < 60

    def test_agent_snooze_not_found(self, client: TestClient, auth_headers: dict):
        """Test POST /agents/{id}/snooze with non-existent agent."""
        response = client.post(
            "/agents/999/snooze?snooze_minutes=10", headers=auth_headers
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_agent_snooze_requires_auth(self, client: TestClient, sample_agent):
        """Test that POST /agents/{id}/snooze requires authentication."""
        response = client.post(f"/agents/{sample_agent.id}/snooze?snooze_minutes=10")
        assert response.status_code == 401


# ============================================================================
# TEST TASK ASSIGNMENT ENDPOINTS
# ============================================================================


class TestTaskAssignmentEndpoints:
    """Test suite for Task Assignment endpoints."""

    def test_assign_task_to_agent(
        self, client: TestClient, sample_task, sample_agent, auth_headers: dict
    ):
        """Test POST /tasks/{id}/assign endpoint."""
        assignment_data = {"task_id": sample_task.id, "agent_id": sample_agent.id}
        response = client.post(
            f"/tasks/{sample_task.id}/assign",
            json=assignment_data,
            headers=auth_headers,
        )
        data = response.json()

        assert response.status_code == 200
        assert data["task_id"] == sample_task.id
        assert data["agent_id"] == sample_agent.id
        assert data["status"] == "pending"
        assert "id" in data
        assert "assigned_at" in data

        # Verify task was updated
        task_response = client.get(f"/tasks/{sample_task.id}")
        task_data = task_response.json()
        assert task_data["assigned_agent_id"] == sample_agent.id

    def test_assign_task_to_agent_requires_auth(
        self, client: TestClient, sample_task, sample_agent
    ):
        """Test that POST /tasks/{id}/assign requires authentication."""
        assignment_data = {"task_id": sample_task.id, "agent_id": sample_agent.id}
        response = client.post(f"/tasks/{sample_task.id}/assign", json=assignment_data)
        assert response.status_code == 401

    def test_assign_task_not_found(
        self, client: TestClient, sample_agent, auth_headers: dict
    ):
        """Test POST /tasks/{id}/assign with non-existent task."""
        assignment_data = {"task_id": 999, "agent_id": sample_agent.id}
        response = client.post(
            "/tasks/999/assign", json=assignment_data, headers=auth_headers
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_assign_task_agent_not_found(
        self, client: TestClient, sample_task, auth_headers: dict
    ):
        """Test POST /tasks/{id}/assign with non-existent agent."""
        assignment_data = {"task_id": sample_task.id, "agent_id": 999}
        response = client.post(
            f"/tasks/{sample_task.id}/assign",
            json=assignment_data,
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_get_task_assignments(
        self,
        client: TestClient,
        session: Session,
        sample_task,
        sample_agent,
        auth_headers: dict,
    ):
        """Test GET /tasks/{id}/assignments endpoint."""
        # Create multiple assignments
        assignments = [
            TaskAssignment(
                task_id=sample_task.id, agent_id=sample_agent.id, status="pending"
            ),
            TaskAssignment(
                task_id=sample_task.id, agent_id=sample_agent.id, status="acknowledged"
            ),
        ]
        for assignment in assignments:
            session.add(assignment)
        session.commit()

        response = client.get(
            f"/tasks/{sample_task.id}/assignments", headers=auth_headers
        )
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 2
        assert all(assignment["task_id"] == sample_task.id for assignment in data)
        assert any(assignment["status"] == "pending" for assignment in data)
        assert any(assignment["status"] == "acknowledged" for assignment in data)

    def test_get_task_assignments_no_auth_required(
        self, client: TestClient, session: Session, sample_task, sample_agent
    ):
        """Test that GET /tasks/{id}/assignments doesn't require authentication."""
        # Create an assignment
        assignment = TaskAssignment(
            task_id=sample_task.id, agent_id=sample_agent.id, status="pending"
        )
        session.add(assignment)
        session.commit()

        response = client.get(f"/tasks/{sample_task.id}/assignments")
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["task_id"] == sample_task.id

    def test_get_task_assignments_task_not_found(
        self, client: TestClient, auth_headers: dict
    ):
        """Test GET /tasks/{id}/assignments with non-existent task."""
        response = client.get("/tasks/999/assignments", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

    def test_reassignment_creates_new_record(
        self,
        client: TestClient,
        session: Session,
        sample_task,
        sample_agent,
        auth_headers: dict,
    ):
        """Test that reassigning a task creates a new assignment record."""
        # Create first agent
        agent1 = Agent(name="First Agent", type="sub_agent")
        session.add(agent1)
        session.commit()
        session.refresh(agent1)

        # First assignment
        assignment_data1 = {"task_id": sample_task.id, "agent_id": agent1.id}
        response1 = client.post(
            f"/tasks/{sample_task.id}/assign",
            json=assignment_data1,
            headers=auth_headers,
        )
        assert response1.status_code == 200

        # Second assignment (reassignment)
        assignment_data2 = {"task_id": sample_task.id, "agent_id": sample_agent.id}
        response2 = client.post(
            f"/tasks/{sample_task.id}/assign",
            json=assignment_data2,
            headers=auth_headers,
        )
        assert response2.status_code == 200

        # Verify we have two assignment records
        assignments_response = client.get(
            f"/tasks/{sample_task.id}/assignments", headers=auth_headers
        )
        assignments = assignments_response.json()
        assert len(assignments) == 2

        # Verify the latest assignment is to sample_agent
        latest_assignment = max(assignments, key=lambda x: x["assigned_at"])
        assert latest_assignment["agent_id"] == sample_agent.id


# ============================================================================
# TEST TASK AGENT FIELDS
# ============================================================================


class TestTaskAgentFields:
    """Test suite for Task agent-related fields."""

    def test_task_assigned_agent_id(
        self, client: TestClient, session: Session, sample_agent, auth_headers: dict
    ):
        """Test task assigned_agent_id field."""
        # Create task with assigned agent
        task = Task(
            name="Task with Agent",
            assigned_agent_id=sample_agent.id,
            ping_interval_minutes=45,
            is_ping_enabled=True,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Verify field is set correctly
        assert task.assigned_agent_id == sample_agent.id

        # Test via API
        response = client.get(f"/tasks/{task.id}")
        data = response.json()
        assert data["assigned_agent_id"] == sample_agent.id

    def test_task_ping_enabled_default(self, client: TestClient, session: Session):
        """Test task ping_enabled field default value."""
        task = Task(name="Default Ping Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.is_ping_enabled is True

        # Test via API
        response = client.get(f"/tasks/{task.id}")
        data = response.json()
        assert data["is_ping_enabled"] is True

    def test_task_ping_interval_default(self, client: TestClient, session: Session):
        """Test task ping_interval_minutes field default value."""
        task = Task(name="Default Interval Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.ping_interval_minutes == 30

        # Test via API
        response = client.get(f"/tasks/{task.id}")
        data = response.json()
        assert data["ping_interval_minutes"] == 30

    def test_task_agent_relationship(self, session: Session, sample_task, sample_agent):
        """Test task-agent relationship works correctly."""
        # Assign agent to task
        sample_task.assigned_agent_id = sample_agent.id
        session.add(sample_task)
        session.commit()
        session.refresh(sample_task)

        # Test relationship from task side
        assert sample_task.assigned_agent.id == sample_agent.id
        assert sample_task.assigned_agent.name == sample_agent.name

        # Test relationship from agent side
        assert sample_agent.current_task.id == sample_task.id
        assert sample_agent.current_task.name == sample_task.name
