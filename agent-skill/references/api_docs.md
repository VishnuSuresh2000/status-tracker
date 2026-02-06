# Status Tracker API Documentation

## Base URL
`http://status-tracker-app:8000` (inside Docker network)
`http://localhost:8000` (local)

## Authentication
All mutation endpoints (POST, PATCH, PUT, DELETE) require a Bearer Token in the `Authorization` header.
The token is stored in `TOOLS.md`.

## Endpoints

### Tasks
- `GET /tasks/`: List all tasks. Returns a list of `TaskRead` objects.
- `GET /tasks/{task_id}`: Get a specific task with all phases and todos.
- `POST /tasks/`: Create a new task.
  - Body: `TaskCreate`
- `PATCH /tasks/{task_id}?status={status}`: Update task status (todo, in_progress, done).
- `PUT /tasks/{task_id}`: Edit task name or interval.
- `DELETE /tasks/{task_id}`: Delete a task.

### Todos & Phases
- `PATCH /todos/{todo_id}`: Update todo status (todo, done).
  - Body: `{"status": "done"}`
- `PATCH /phases/{phase_id}`: Update phase status.
  - Body: `{"status": "completed"}`

### Comments
- `GET /tasks/{task_id}/comments`: Get all comments for a task.
- `POST /tasks/{task_id}/comments`: Add a comment.
  - Body: `{"text": "my comment", "author": "agent"}`

## Data Models

### TaskCreate
```json
{
  "name": "string",
  "description": "string",
  "priority": "low|medium|high|critical",
  "interval_minutes": 60.0,
  "phases": [
    {
      "name": "Phase Name",
      "order": 1,
      "todos": [
        { "name": "Todo Name" }
      ]
    }
  ]
}
```
