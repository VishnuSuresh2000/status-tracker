---
name: status-tracker-app
description: "Manage and track project tasks, phases, and todos using the Status Tracker app. Use when you need to: (1) Create new tasks for your current assignment, (2) Update progress on tasks/todos, (3) Report completion of milestones."
---

# Status Tracker Skill

This skill allows you to interact with the Status Tracker application to maintain a structured log of work progress.

## 🤖 Auto-Task Detection Rules

**Automatically create a task when ANY of these conditions are met:**

### Trigger Conditions (CREATE TASK):
1. **Multi-step work** - Any request requiring 3+ actions
2. **Time investment** - Work estimated to take 15+ minutes
3. **Project phases** - Requests mentioning phases, milestones, or stages
4. **Recurring work** - Tasks that need periodic attention
5. **User explicitly asks** - "track this", "create a task", "add to tracker"
6. **Bug fixes & UI improvements** - Any fix, patch, or enhancement to existing features
7. **Infrastructure/Deployment fixes** - Traefik caching, Docker issues, network problems

### Skip Conditions (NO TASK):
- Simple questions (single answer)
- Quick lookups (read file, check status)
- Casual conversation
- Immediate one-step actions

## 🔄 Task Lifecycle Management

### Starting Work:
1. **Mark first todo as `in_progress`** → Task auto-moves to `in_progress`
2. API: `PATCH /todos/{id}` with `{"status": "in_progress"}`

### Completing Items:
1. **Mark todo as `done`** immediately after completing it
2. **Mark phase as `completed`** when all todos done
3. Progress auto-recalculates based on completion

### Task Completion:
1. All phases must be `completed` before marking task as `done`
2. Hard validation blocks incomplete tasks from being `done`
3. Add summary comment when finishing

### Example Flow:
```
1. Start work → PATCH /todos/1 {"status": "in_progress"}
2. Task auto → "in_progress" (progress > 0%)
3. Finish todo → PATCH /todos/1 {"status": "done"}
4. Start next → PATCH /todos/2 {"status": "in_progress"}
5. ... repeat ...
6. All done → PATCH /tasks/{id}?status=done
```

**⚠️ NEVER skip updating todos while working!** This ensures real-time progress visibility.

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

## Task Creation Template

```
Name: [Clear action-oriented title]
Priority: medium (high if urgent/important)
Phases: Break into logical steps if complex
Description: Context and goal
```

## Task Update Triggers

- **Start work** → Set status to `in_progress`
- **Complete milestone** → Mark phase/todo as done, add comment
- **Finish task** → Set status to `done`, add summary comment
- **Blockers** → Add comment explaining issue

## References

- [API Documentation](references/api_docs.md): Full endpoint list and data schemas.
- [ROUTINE.md](../../ROUTINE.md): Mandatory AI agent instructions.
