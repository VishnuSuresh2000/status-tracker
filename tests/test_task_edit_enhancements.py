import pytest
from fastapi.testclient import TestClient
from main import Task

MINIMAL_TASK = {
    "name": "Enhancement Task",
    "priority": "medium",
    "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
}

def test_edit_task_all_new_fields(client: TestClient, auth_headers: dict):
    # Create task
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    # Update all new fields
    edit_data = {
        "name": "Updated Enhancement Task",
        "description": "New description",
        "priority": "high",
        "skills": "skill1, skill2",
        "flow_chart": "graph TD\nA --> B",
        "interval_minutes": 15.0
    }
    response = client.put(f"/tasks/{task_id}", json=edit_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Enhancement Task"
    assert data["description"] == "New description"
    assert data["priority"] == "high"
    assert data["skills"] == "skill1, skill2"
    assert data["flow_chart"] == "graph TD\nA --> B"
    assert data["interval_minutes"] == 15.0

def test_edit_task_clear_skills_and_flowchart(client: TestClient, auth_headers: dict):
    # Create task with fields
    task_data = MINIMAL_TASK.copy()
    task_data["skills"] = "existing skill"
    task_data["flow_chart"] = "existing chart"
    response = client.post("/tasks/", json=task_data, headers=auth_headers)
    task_id = response.json()["id"]

    # Clear fields
    response = client.put(f"/tasks/{task_id}", json={"skills": "", "flow_chart": "  "}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["skills"] is None
    assert data["flow_chart"] is None

def test_edit_task_partial_update(client: TestClient, auth_headers: dict):
    # Create task
    response = client.post("/tasks/", json=MINIMAL_TASK, headers=auth_headers)
    task_id = response.json()["id"]

    # Update only priority
    response = client.put(f"/tasks/{task_id}", json={"priority": "critical"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["priority"] == "critical"
    assert data["name"] == "Enhancement Task" # Should remain unchanged
