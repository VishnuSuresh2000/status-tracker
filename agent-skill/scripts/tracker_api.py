import os
import json
import sys
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, List, Dict, Any

# Default API configuration
API_BASE_URL = os.getenv("STATUS_TRACKER_URL", "http://status-tracker-app:8000")
AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")


class StatusTrackerAPI:
    def __init__(self, base_url: str = API_BASE_URL, token: str = AUTH_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}" if self.token else "",
        }

    def _request(
        self, method: str, path: str, data: Any = None, params: Dict[str, str] = None
    ):
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url, data=req_data, headers=self.headers, method=method
        )

        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 204:
                    return True
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"Error: {e.code} {e.reason}", file=sys.stderr)
            print(f"Response: {e.read().decode('utf-8')}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Connection Error: {e}", file=sys.stderr)
            return None

    def list_tasks(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/tasks/")

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/tasks/{task_id}")

    def create_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._request("POST", "/tasks/", data=task_data)

    def update_task_status(self, task_id: int, status: str) -> Optional[Dict[str, Any]]:
        return self._request("PATCH", f"/tasks/{task_id}", params={"status": status})

    def update_todo(self, todo_id: int, status: str) -> Optional[Dict[str, Any]]:
        return self._request("PATCH", f"/todos/{todo_id}", data={"status": status})

    def add_comment(
        self, task_id: int, text: str, author: str = "agent"
    ) -> Optional[Dict[str, Any]]:
        return self._request(
            "POST", f"/tasks/{task_id}/comments", data={"text": text, "author": author}
        )


if __name__ == "__main__":
    # Simple CLI wrapper
    if len(sys.argv) < 2:
        print("Usage: python tracker_api.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    api = StatusTrackerAPI()

    if command == "list":
        tasks = api.list_tasks()
        if tasks is not None:
            print(json.dumps(tasks, indent=2))
    elif command == "get" and len(sys.argv) > 2:
        task = api.get_task(int(sys.argv[2]))
        if task is not None:
            print(json.dumps(task, indent=2))
    elif command == "create" and len(sys.argv) > 2:
        task_data = json.loads(sys.argv[2])
        task = api.create_task(task_data)
        if task is not None:
            print(json.dumps(task, indent=2))
    elif command == "status" and len(sys.argv) > 3:
        task = api.update_task_status(int(sys.argv[2]), sys.argv[3])
        if task is not None:
            print(json.dumps(task, indent=2))
    elif command == "todo" and len(sys.argv) > 3:
        todo = api.update_todo(int(sys.argv[2]), sys.argv[3])
        if todo is not None:
            print(json.dumps(todo, indent=2))
    elif command == "comment" and len(sys.argv) > 3:
        comment = api.add_comment(int(sys.argv[2]), sys.argv[3])
        if comment is not None:
            print(json.dumps(comment, indent=2))
    else:
        print(f"Unknown command or missing args: {command}")
        sys.exit(1)
