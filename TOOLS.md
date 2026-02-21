# TOOLS.md - Local Configuration

## Status Tracker API

- **URL:** http://status-tracker-app:8000 (Docker: http://status-tracker-app:8000)
- **Auth Token:** `d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA=`
- **Script:** `/home/node/.openclaw/workspace/status-tracker/scripts/tracker_api.py`

### Quick Commands
```bash
# List tasks
TRACKER_AUTH_TOKEN="d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA=" python scripts/tracker_api.py list

# Create task
TRACKER_AUTH_TOKEN="d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA=" python scripts/tracker_api.py create '{"name": "Task Name", "priority": "high"}'

# Update status
TRACKER_AUTH_TOKEN="d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA=" python scripts/tracker_api.py status <task_id> in_progress
```
