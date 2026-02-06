---
name: status-tracker-app
description: "Manage and track project tasks, phases, and todos using the Status Tracker app. Use when you need to: (1) Check for ongoing work at startup, (2) Create new tasks for your current assignment, (3) Update progress on tasks/todos, (4) Report completion of milestones, or (5) Ask for permission to continue work found in the tracker."
---

# Status Tracker Skill

This skill allows you to interact with the Status Tracker application to maintain a structured log of work progress.

## Mandatory Routine

1.  **On Startup**: Read `ROUTINE.md` in the project root and check the Status Tracker for existing `in_progress` tasks.
2.  **Authorization**: If ongoing tasks are found, present them to the user and ask: "Can I continue with the ongoing process in the Status Tracker?"
3.  **Track Everything**: Create a task for every new assignment. Use phases and todos for complex work.
4.  **Report Progress**: Update status and add comments as you work.

## Tools

Use the `tracker_api.py` script to interact with the API.

### Usage Examples

**List all tasks**:
```bash
python scripts/tracker_api.py list
```

**Create a new task**:
```bash
python scripts/tracker_api.py create '{"name": "Implement Feature X", "priority": "high"}'
```

**Update todo status**:
```bash
python scripts/tracker_api.py todo <todo_id> "done"
```

**Add a progress comment**:
```bash
python scripts/tracker_api.py comment <task_id> "Finished the database migration phase."
```

## References

- [API Documentation](references/api_docs.md): Full endpoint list and data schemas.
- [ROUTINE.md](../ROUTINE.md): Mandatory AI agent instructions.
