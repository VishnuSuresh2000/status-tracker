#!/usr/bin/env python3
"""
Ruto's Status Tracker API Client
Used for auto-task detection and management.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone

# Configuration
TRACKER_URL = os.environ.get("TRACKER_URL", "http://localhost:8000")
AUTH_TOKEN = os.environ.get("TRACKER_AUTH_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def api_call(method, endpoint, data=None, params=None):
    """Make API call to status tracker."""
    url = f"{TRACKER_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        elif method == "POST":
            resp = requests.post(url, headers=HEADERS, json=data, timeout=10)
        elif method == "PATCH":
            resp = requests.patch(url, headers=HEADERS, json=data, timeout=10)
        elif method == "DELETE":
            resp = requests.delete(url, headers=HEADERS, timeout=10)
        else:
            return {"error": f"Unknown method: {method}"}
        
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
    except Exception as e:
        return {"error": str(e)}

def list_tasks(status=None):
    """List all tasks or filter by status."""
    params = {"status": status} if status else None
    return api_call("GET", "/tasks/", params=params)

def create_task(name, priority="medium", description=None, interval_minutes=60):
    """Create a new task."""
    data = {
        "name": name,
        "priority": priority,
        "interval_minutes": interval_minutes
    }
    if description:
        data["description"] = description
    return api_call("POST", "/tasks/", data=data)

def get_task(task_id):
    """Get task details."""
    return api_call("GET", f"/tasks/{task_id}")

def update_task(task_id, **kwargs):
    """Update task fields."""
    return api_call("PATCH", f"/tasks/{task_id}", data=kwargs)

def update_task_status(task_id, status):
    """Update task status (todo/in_progress/done)."""
    # The API currently uses query parameters for status
    url = f"{TRACKER_URL}/tasks/{task_id}"
    try:
        resp = requests.patch(url, headers=HEADERS, params={"status": status}, timeout=10)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
    except Exception as e:
        return {"error": str(e)}

def delete_task(task_id):
    """Delete a task."""
    return api_call("DELETE", f"/tasks/{task_id}")

def add_comment(task_id, text, author="Ruto"):
    """Add a comment to a task."""
    return api_call("POST", f"/tasks/{task_id}/comments", data={
        "text": text,
        "author": author
    })

def add_phase(task_id, name, order=1):
    """Add a phase to a task."""
    task = get_task(task_id)
    if "error" in task:
        return task
    phases = task.get("phases", [])
    phases.append({
        "name": name,
        "order": order,
        "status": "not_started",
        "todos": []
    })
    return api_call("PUT", f"/tasks/{task_id}", data={"phases": phases})

def add_todo(task_id, phase_id, name):
    """Add a todo to a phase."""
    task = get_task(task_id)
    if "error" in task:
        return task
    phases = task.get("phases", [])
    for phase in phases:
        if phase.get("id") == phase_id:
            phase["todos"].append({
                "name": name,
                "status": "todo"
            })
    return api_call("PUT", f"/tasks/{task_id}", data={"phases": phases})

def update_todo_status(task_id, phase_id, todo_id, status):
    """Update todo status."""
    task = get_task(task_id)
    if "error" in task:
        return task
    phases = task.get("phases", [])
    for phase in phases:
        if phase.get("id") == phase_id:
            for todo in phase.get("todos", []):
                if todo.get("id") == todo_id:
                    todo["status"] = status
    return api_call("PUT", f"/tasks/{task_id}", data={"phases": phases})

def batch_report(task_id, updates):
    """Send batch report with multiple updates."""
    return api_call("POST", f"/tasks/{task_id}/batch-report", data=updates)

# Agent-specific functions
def get_my_pings():
    """Get pending pings for Ruto."""
    return api_call("GET", "/agents/", params={"name": "Ruto"})

def acknowledge_ping(task_id):
    """Acknowledge a task assignment."""
    return api_call("POST", f"/agents/1/acknowledge", params={"task_id": task_id})

def snooze_ping(minutes=30):
    """Snooze current ping."""
    return api_call("POST", "/agents/1/snooze", params={"snooze_minutes": minutes})

def main():
    """CLI interface for tracker API."""
    if len(sys.argv) < 2:
        print("Usage: tracker_api.py <command> [args]")
        print("\nCommands:")
        print("  list                          - List all tasks")
        print("  create '<json>'               - Create task from JSON")
        print("  get <task_id>                 - Get task details")
        print("  update <task_id> '<json>'     - Update task fields")
        print("  status <task_id> <status>     - Update task status")
        print("  comment <task_id> '<text>'    - Add comment")
        print("  delete <task_id>              - Delete task")
        print("\nExamples:")
        print("  tracker_api.py list")
        print("  tracker_api.py create '{\"name\": \"New Task\", \"priority\": \"high\"}'")
        print("  tracker_api.py status 1 in_progress")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        result = list_tasks()
        print(json.dumps(result, indent=2))
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: create requires JSON data")
            sys.exit(1)
        data = json.loads(sys.argv[2])
        result = create_task(**data)
        print(json.dumps(result, indent=2))
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: get requires task_id")
            sys.exit(1)
        result = get_task(int(sys.argv[2]))
        print(json.dumps(result, indent=2))
    
    elif command == "update":
        if len(sys.argv) < 4:
            print("Error: update requires task_id and JSON data")
            sys.exit(1)
        task_id = int(sys.argv[2])
        data = json.loads(sys.argv[3])
        result = update_task(task_id, **data)
        print(json.dumps(result, indent=2))
    
    elif command == "status":
        if len(sys.argv) < 4:
            print("Error: status requires task_id and new status")
            sys.exit(1)
        task_id = int(sys.argv[2])
        status = sys.argv[3]
        result = update_task_status(task_id, status)
        print(json.dumps(result, indent=2))
    
    elif command == "comment":
        if len(sys.argv) < 4:
            print("Error: comment requires task_id and text")
            sys.exit(1)
        task_id = int(sys.argv[2])
        text = sys.argv[3]
        result = add_comment(task_id, text)
        print(json.dumps(result, indent=2))
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: delete requires task_id")
            sys.exit(1)
        result = delete_task(int(sys.argv[2]))
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
