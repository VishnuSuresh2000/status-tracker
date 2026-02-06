# Status Tracker

A FastAPI-based task management system with background worker monitoring, real-time notifications, and a visual Kanban-style dashboard. Built through human-AI collaboration.

## Features

- **Task Management**: Create, read, update, and delete tasks
- **Kanban Board**: Visual task board with columns for To Do, In Progress, and Done
- **Background Worker**: Monitors in-progress tasks and sends notifications
- **Real-time Notifications**: In-app notification system for task reminders and updates
- **RESTful API**: Complete CRUD operations via HTTP endpoints
- **Responsive UI**: Built with Tailwind CSS

## Tech Stack

- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: HTML + JavaScript + Tailwind CSS
- **Background Processing**: Python worker with Redis
- **Database**: SQLite with SQLModel ORM
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

1. **Environment Setup**: Copy the example environment file and configure it:
```bash
cp .env.example .env
# Edit .env and set your API_AUTH_TOKEN and HOST_NAME
```

Generate a secure API token:
```bash
openssl rand -base64 32
```

### Using Docker Compose (Recommended)

```bash
cd status-tracker
docker-compose up -d
```

The application will be available at `http://localhost:8000`

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
uvicorn main:app --reload
```

3. Start the worker (in a separate terminal):
```bash
python worker.py
```

## API Endpoints

### Authentication

API endpoints marked with 🔒 require Bearer token authentication. Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer $API_AUTH_TOKEN" http://localhost:8000/tasks/
```

### Tasks

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/tasks/` | Public | List all tasks |
| GET | `/tasks/{task_id}` | Public | Get specific task details |
| POST | `/tasks/` | 🔒 | Create a new task |
| PATCH | `/tasks/{task_id}` | 🔒 | Update task status |
| PUT | `/tasks/{task_id}` | 🔒 | Edit task details |
| DELETE | `/tasks/{task_id}` | 🔒 | Delete a task |

**Create Task** (POST /tasks/):
```json
{
  "name": "My Task",
  "description": "Optional description",
  "interval_minutes": 60.0,
  "status": "todo"
}
```

### Notifications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications/` | Public | List all notifications |
| GET | `/notifications/unread-count` | Public | Get count of unread notifications |
| PATCH | `/notifications/{notification_id}/read` | 🔒 | Mark notification as read |
| POST | `/notifications/read-all` | 🔒 | Mark all notifications as read |

## Data Models

### Task

| Field | Type | Description |
|-------|------|-------------|
| id | int | Auto-incrementing primary key |
| name | str | Task name |
| status | str | Current status: `todo`, `in_progress`, `done` |
| interval_minutes | float | Notification interval in minutes |
| last_ping | datetime | Last time a notification was sent |
| created_at | datetime | Task creation timestamp |

### Notification

| Field | Type | Description |
|-------|------|-------------|
| id | int | Auto-incrementing primary key |
| task_id | int | Reference to the task |
| task_name | str | Name of the task |
| message | str | Notification message |
| notification_type | str | Type: `reminder`, `completion`, `system` |
| is_read | bool | Read status |
| created_at | datetime | Notification timestamp |

## Worker

The background worker (`worker.py`) monitors tasks with status `in_progress`:

- Checks every 30 seconds for tasks that need reminders
- Sends notifications when `interval_minutes` have passed since `last_ping`
- Updates `last_ping` to prevent spam
- Creates notifications in the database

## File Structure

```
status-tracker/
├── data/                   # SQLite database storage
│   └── .gitkeep           # Keeps directory in git
├── .env.example           # Environment variable template
├── main.py                # FastAPI application
├── notifications.py       # Notification module
├── worker.py              # Background worker
├── index.html             # Frontend UI
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker orchestration
├── Dockerfile             # Container definition
├── pyproject.toml         # Project metadata
└── README.md              # This file
```

## Environment Variables

Create a `.env` file by copying `.env.example`:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_AUTH_TOKEN` | Bearer token for API authentication (required for write operations) | `openssl rand -base64 32` |
| `HOST_NAME` | Domain for Traefik routing (Docker deployments only) | `status-tracker.local` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/tasks.db` |
| `REDIS_HOST` | Redis server hostname | `localhost` |

**Security Note**: Never commit `.env` to version control. It's already in `.gitignore`.

## Running Tests

```bash
pytest
```

## Troubleshooting

### API Authentication Errors (401 Unauthorized)
- Ensure `API_AUTH_TOKEN` is set in your `.env` file
- Include the token in request headers: `Authorization: Bearer <token>`
- Verify the token matches between your client and server

### Database Issues
- Ensure the `data/` directory exists: `mkdir -p data`
- Check write permissions on the `data/` directory
- The database file (`tasks.db`) is automatically created on first run

### Worker Not Running
- Verify Redis is running: `docker-compose ps` or `redis-cli ping`
- Check worker logs: `docker-compose logs worker`
- Ensure `REDIS_HOST` is correctly set in `.env`

### Docker Compose Issues
- Ensure `.env` file exists and contains required variables
- Check Traefik network exists: `docker network create traefik` (if using Traefik)
- View service logs: `docker-compose logs -f [service-name]`

## Deployment

The application includes Docker Compose configuration for easy deployment. The compose file includes:

- **app**: FastAPI web application with Traefik integration
- **worker**: Background task processor
- **redis**: Message broker for background tasks

Key features:
- Persistent data storage via Docker volumes
- Automatic HTTPS with Traefik (optional)
- Health checks and restart policies

See `docker-compose.yml` for full configuration.

## Development

### Adding New Features

1. Add API endpoint in `main.py`
2. Update models if needed in `main.py` or `notifications.py`
3. Modify UI in `index.html`
4. Update worker logic in `worker.py` if needed
5. Write tests
6. Update documentation

### Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Keep functions focused and small
- Add docstrings for public functions

## Credits

**Created by**: Ruto (AI Assistant)  
**In collaboration with**: Vishnu Suresh

This project demonstrates the power of human-AI collaboration in software development, combining AI-driven implementation with human guidance, testing, and refinement.

## License

MIT License

## Changelog

### Phase 1 (Completed)

- Added data directory structure
- Implemented task deletion functionality (DELETE endpoint + UI)
- Implemented task editing functionality (PUT endpoint + edit modal)
- Replaced worker ping with real notification system
- Added notification API endpoints
- Added notification UI (bell icon + panel)
- Updated documentation
