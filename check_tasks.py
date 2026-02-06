import requests
import json

API_BASE_URL = "http://status-tracker-app:8000"

def check_tasks():
    for tid in [1, 4]:
        response = requests.get(f"{API_BASE_URL}/tasks/{tid}")
        if response.status_code == 200:
            task = response.json()
            print(f"Task {tid}: {task['name']} - Progress: {task['progress_percent']}% - Status: {task['status']}")
        else:
            print(f"Task {tid} not found (Status {response.status_code})")

if __name__ == "__main__":
    check_tasks()
