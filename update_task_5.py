import requests

API_BASE_URL = "http://status-tracker-app:8000"
AUTH_TOKEN = "d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA="

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def update_task_5():
    # Mark task 5 as completed via batch report
    reports = [
        {"comment": "Completed Phase 4, sub-agent support, and verified project status.", "author": "agent"},
        {"task_status": "done"}
    ]
    
    response = requests.post(
        f"{API_BASE_URL}/tasks/5/batch-report",
        headers=headers,
        json=reports
    )
    print(f"Update Task 5 Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    update_task_5()
