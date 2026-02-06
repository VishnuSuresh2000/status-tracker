import requests
import json
import os

API_BASE_URL = "http://status-tracker-app:8000"
AUTH_TOKEN = "d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA="

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_batch_report():
    print("\n--- Testing Batch Report ---")
    
    # 1. Get Task 1 to find a todo_id and phase_id
    response = requests.get(f"{API_BASE_URL}/tasks/1")
    if response.status_code != 200:
        print(f"Error: Could not find Task 1 (Status {response.status_code})")
        return
    
    task = response.json()
    if not task.get("phases"):
        print("Error: Task 1 has no phases")
        return
    
    phase = task["phases"][0]
    phase_id = phase["id"]
    todo_id = phase["todos"][0]["id"] if phase.get("todos") else None
    
    print(f"Targeting Task 1, Phase {phase_id}, Todo {todo_id}")
    
    # 2. Send Batch Report
    reports = [
        {"comment": "Testing batch report from sub-agent", "author": "sub-agent"},
        {"phase_id": phase_id, "status": "in_progress"}
    ]
    
    if todo_id:
        reports.append({"todo_id": todo_id, "status": "done"})
        
    response = requests.post(
        f"{API_BASE_URL}/tasks/1/batch-report",
        headers=headers,
        json=reports
    )
    
    print(f"Batch Report Status: {response.status_code}")
    print(f"Batch Report Response: {response.json()}")
    
    # 3. Verify Progress
    response = requests.get(f"{API_BASE_URL}/tasks/1")
    updated_task = response.json()
    print(f"Updated Progress: {updated_task['progress_percent']}%")
    
    # 4. Mark Task 1 and 4 as Completed
    print("\n--- Marking Tasks 1 and 4 as Completed ---")
    for tid in [1, 4]:
        # To mark a task as completed properly in this system, we mark its phases as completed
        task_resp = requests.get(f"{API_BASE_URL}/tasks/{tid}")
        if task_resp.status_code == 200:
            t = task_resp.json()
            p_reports = []
            for p in t.get("phases", []):
                p_reports.append({"phase_id": p["id"], "status": "completed"})
            
            if p_reports:
                res = requests.post(
                    f"{API_BASE_URL}/tasks/{tid}/batch-report",
                    headers=headers,
                    json=p_reports
                )
                print(f"Task {tid} Completion Status: {res.status_code}")
            else:
                # If no phases, use legacy status update
                res = requests.patch(
                    f"{API_BASE_URL}/tasks/{tid}?status=done",
                    headers=headers
                )
                print(f"Task {tid} Legacy Completion Status: {res.status_code}")

if __name__ == "__main__":
    test_batch_report()
