
import os
import requests

TRACKER_URL = "http://status-tracker-app:8000"
TRACKER_AUTH_TOKEN = "d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA="
HEADERS = {
    "Authorization": f"Bearer {TRACKER_AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def update_todo(task_id, todo_id, status):
    resp = requests.patch(f"{TRACKER_URL}/todos/{todo_id}", headers=HEADERS, json={"status": status})
    print(f"Todo {todo_id} status updated to {status}: {resp.status_code}")

def update_phase(phase_id, status):
    resp = requests.patch(f"{TRACKER_URL}/phases/{phase_id}", headers=HEADERS, json={"status": status})
    print(f"Phase {phase_id} status updated to {status}: {resp.status_code}")

# Update todos for Phase 1 (Audit current setup)
update_todo(44, 188, "done")
update_todo(44, 189, "done")
update_phase(76, "completed")

# Update todo for Phase 2 (Fix and optimize)
update_todo(44, 190, "done") # Prompt and tool URLs updated
update_todo(44, 191, "in_progress") # Delivery settings verified
