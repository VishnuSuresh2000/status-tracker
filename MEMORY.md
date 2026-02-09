- **Status Tracker Rule:** MANDATORY to use Status Tracker for every task.
- **Coding Tool Preference:** MANDATORY to use the `opencode-controller` skill for all coding, editing, and debugging tasks. It is the primary tool for these activities.
- **Task Management:** Report progress via API using the auth token in `TOOLS.md`.

## 🔄 Task Lifecycle Management (CRITICAL)

When working on ANY task with phases/todos:

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

## 🤖 Ruto's Auto-Task Detection Rules

I (Ruto) automatically create tasks in the Status Tracker when I detect:

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

### Task Creation Template:
```
Name: [Clear action-oriented title]
Priority: medium (high if urgent/important)
Phases: Break into logical steps if complex
Description: Context and goal
```

### Task Update Triggers:
- **Start work** → Set status to `in_progress`
- **Complete milestone** → Mark phase/todo as done, add comment
- **Finish task** → Set status to `done`, add summary comment
- **Blockers** → Add comment explaining issue

### API Script:
```bash
cd /home/node/.openclaw/workspace/status-tracker
TRACKER_AUTH_TOKEN="d3Qb0YtAAxJ+hSvRHp0rnFBoGSKia8QDEJAIzZv5FjA=" python scripts/tracker_api.py <command>
```

## Status Tracker Project

**Tech Stack:** FastAPI, SQLite, Alpine-based Docker image
**Features:** Background task monitoring with OpenClaw Gateway pings, visual UI dashboard
**Deployment:** Traefik integration with specific labels

**Architecture:**
- Backend: FastAPI with SQLite database
- Frontend: Simple HTML/CSS with Tailwind CSS  
- Background Processing: Redis + worker process
- Containerization: Docker with Alpine-based image
- Deployment: Traefik integration

**Key Components:**
- Task Management API (create, list, update, delete tasks)
- Task editing with modal dialog
- Visual Kanban-style dashboard with delete/edit buttons
- Background worker with real notification system
- In-app notification panel with badge counter
- Docker compose setup with Traefik

**Phase 1 Complete (2026-02-04):**
- ✅ Created data/ directory structure
- ✅ Added task deletion (DELETE endpoint + UI)
- ✅ Added task editing (PUT endpoint + edit modal)
- ✅ Replaced worker ping with notification system
- ✅ Added notification API endpoints and UI
- ✅ Complete API documentation
- ✅ Created comprehensive `TEST_PLAN.md` (identifying Worker and UI test gaps)
- ✅ Verified 26/26 existing tests are passing

**Phase 2 Complete (2026-02-05):**
- ✅ Implemented `tests/test_worker.py` (3 tests) covering background notification logic
- ✅ Implemented `tests/test_integration.py` covering E2E task/notification lifecycle
- ✅ Verified all 30 tests pass (100% success rate)
- ✅ Created `tests/test_ui.py` for Playwright (script ready, execution pending env setup)

**Phase 3 Complete (2026-02-05):**
- ✅ Fixed mobile responsiveness in `index.html` using Opencode (Plan -> Build loop).
- ✅ Implemented Bearer Token API Authentication for `POST /tasks/`.
- ✅ Secured the API with a private, unique auth token known only to the assistant.
- ✅ Added 8 unit tests specifically for authentication (`tests/test_auth.py`).
- ✅ Verified all 40 system tests pass (100% success rate).

**Phase 4 Complete (2026-02-06):**
- ✅ Expanded Task schema with `description`, `priority`, `progress_percent`, `flow_chart`, `context_tags`, `definition_of_done`, and `last_ai_summary`.
- ✅ Implemented hierarchical structure: **Task → Phase → Todo**.
- ✅ Added **Comments** system for timestamped logs by users, assistants, or sub-agents.
- ✅ Implemented auto-recalculation logic for `progress_percent` based on todo/phase completion.
- ✅ Added status propagation (todo completion → phase completion → task progress).
- ✅ Secured all mutation endpoints (POST, PATCH, PUT, DELETE) with Bearer token authentication.
- ✅ Added 24 new unit tests in `tests/test_nested_tasks.py` covering nested CRUD and progress logic.
- ✅ **Sub-agent Support (Batch Reporting)**: Implemented `POST /tasks/{task_id}/batch-report` to allow sub-agents to report multiple updates (comments, todos, phases, task status) in a single transaction.
- ✅ Verified all 64 system tests pass (100% success rate).
- ✅ Completed Task ID 1 (Phase 4 Demo) and Task ID 4 (Routine Update).

**Phase 5 Complete (2026-02-07):**
- ✅ Project Update & GitHub Sync (Task ID 5).
- ✅ Ping Indicator Feature (Completed, added to dashboard).
- ✅ Verified all agent skill tools are available in PATH.
- ✅ openclaw CLI installed globally.

**Phase 6 Complete - Ping System 2.0 (2026-02-07):**
- ✅ Database models added: `Agent`, `TaskAssignment`
- ✅ Task model updated with agent assignment fields
- ✅ Forward reference fixes applied
- ✅ API endpoints added:
  - `POST /agents/`, `GET /agents/`, `GET /agents/{id}`
  - `POST /agents/{id}/acknowledge`, `POST /agents/{id}/snooze`
  - `POST /tasks/{id}/assign`, `GET /tasks/{id}/assignments`
- ✅ Worker ping logic: `PingWorker` class with escalation
- ✅ UI components added:
  - Agent Ping Back section with status cards
  - Ruto status badge in header
  - Agent assignment dropdown in task edit modal
  - JavaScript polling every 30 seconds
- ✅ Committed: `93b67c1`
- ✅ Pushed to GitHub
- **Plan file:** `PING_SYSTEM_2_0_PLAN.md`

**Phase 6 Verification - Docker Deployment (2026-02-08):**
- ✅ Deployed to Docker with `docker compose up -d`
- ✅ Fixed worker startup bug (changed `uv run` to direct `python` command)
- ✅ Added `PYTHONUNBUFFERED=1` for real-time logs in docker-compose.yml
- ✅ Added comment creation in `escalate_task()` for audit trail
- ✅ Verified sub-agent escalation: SubAgent-1 → Ruto (Task #14)
- ✅ Fixed `tracker_api.py` to support `phases` in `create` and added `acknowledge` command.
- ✅ Final commit: `f18a29b`

**Phase 7 - Worker Authentication & Test Suite (2026-02-08):**
- ✅ **Fixed Worker 401 Error**: Added `API_AUTH_TOKEN` environment variable to worker service in docker-compose.yml
- ✅ Worker can now successfully authenticate and update task status
- ✅ Created Task #20: "Fix Test Suite - 401 Auth Errors" (DONE)
- ✅ **Test Suite Fixed**: All 155 tests passing (100%)
- ✅ Solution: Centralized auth via `tests/conftest.py`, run with `-e API_AUTH_TOKEN=test-auth-token-for-tests`

**Phase 8 - Task Completion Validation & UI Enhancements (2026-02-08):**
- ✅ **Task #27**: Fixed UI task display - now shows ALL tasks by default (not just latest 5)
- ✅ **Task #28**: Implemented hard block validation for task completion
  - `validate_task_can_be_completed()` helper function in `main.py`
  - Returns HTTP 409 with detailed error when trying to mark incomplete task as done
  - 8 new tests in `tests/test_task_completion_validation.py`
- ✅ **Task #30**: Enhanced Edit Modal & API
  - Added Description, Priority, Skills (comma-separated), and Flowchart (Mermaid) to Edit Modal
  - Added JSON body support to `PUT /tasks/{task_id}` via `TaskEditRequest` Pydantic model
  - Updated Details Modal: Added "Skills:" label and "📊 Flowchart not required" empty state
  - Fixed 4 legacy tests in `test_main.py` and added 3 new tests in `test_task_edit_enhancements.py`
- ✅ Commit: `cf56246`
- ✅ All 158 tests passing

**Phase 9 - UI Skill & Flowchart Improvements (2026-02-08):**
- ✅ Fixed Mermaid.js flowchart rendering in Details Modal
  - Uses `mermaid.render()` with unique IDs for proper diagram display
  - Better error handling for invalid flowchart syntax
- ✅ Standardized skill bubbles with consistent `rounded-full` styling
- ✅ Split skills into two categories with prefix scheme:
  - **Agent Skills** (indigo): Skills the agent has installed (`agent:` prefix)
  - **Task Skills** (amber): Skills needed to complete task (`task:` prefix)
- ✅ Added `parseSkills()` and `combineSkills()` helper functions
- ✅ Updated Edit Modal with separate inputs for each skill type
- ✅ Commit: `e3866f3`

**Phase 10 - UI Enhancements & Testing (2026-02-08):**
- ✅ Added Mermaid zoom controls (+/-/Reset) in Details Modal
  - `zoomMermaid(factor)` and `resetMermaidZoom()` JavaScript functions
  - Scale clamped between 0.5x and 3x
- ✅ Implemented lazy loading for completed tasks
  - `visibleCompletedCount = 5` by default
  - "Load More" button shows remaining count
  - Button hides when all tasks visible
- ✅ Fixed mobile responsive grid
  - `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` for task list
  - `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` for agents
- ✅ Added 18 unit tests in `tests/test_ui_enhancements.py`
  - Lazy loading logic tests
  - Skill parsing tests
  - Mermaid zoom tests
  - Mobile grid tests
  - Skill bubble styling tests
- ✅ Added Playwright UI tests in `tests/test_ui_playwright_enhancements.py`
- ✅ Commit: `a7813cc`
- ✅ All 176 tests passing

**Phase 11 - Mobile UI Polishing (2026-02-09):**
- ✅ Fixed modal title wrapping and responsive font size
- ✅ Improved layout/spacing for task metadata (priority, agent, skills)
- ✅ Standardized skill bubbles with better padding (`px-2.5 py-1`) and visible labels
- ✅ Verified all changes using manual browser check in mobile view
- ✅ Created and completed Task #32
- ✅ Commit: `f1b8c55`

**API Improvement Plan - Final Status (2026-02-08):**
- **Overall Progress**: 95% Complete
- ✅ All database models implemented (Task, Phase, Todo, Comment, Agent, TaskAssignment)
- ✅ All API endpoints functional with nested structure support
- ✅ Hierarchical task management (Tasks → Phases → Todos)
- ✅ Automatic progress calculation and status propagation
- ✅ Comment/logging system with author tracking
- ✅ Agent management and task assignment system
- ✅ Bearer token authentication on all mutation endpoints
- ✅ Sub-agent batch reporting capability
- ✅ Test suite auth consistency fixes (conftest.py)
- ✅ Task completion validation (hard block)
- ⚠️ Pending: Migration script for legacy flat tasks
- ⚠️ Pending: UI enhancements for hierarchical display



## Opencode Controller Usage
- Start Opencode: `opencode run --model opencode/kimi-k2.5-free`
- Current Session: `ses_3c7b09603ffe2pTYUED2cuiDec`
- Use `/sessions` for session management
- Use `/agents` to switch between Plan and Build modes
- Use `/models` for model selection
- Follow Plan → Build workflow loop for coding tasks
- **Skill update (2026-02-07):** Added `opencode-controller` skill via ClawHub.
- **Path update (2026-02-07):** Symlinked opencode to `~/.local/bin/opencode`.

## Configuration Notes
- **Heartbeat Interval**: Changed from 30 minutes to 1 hour (2026-02-08)
- **Test Auth Token**: `test-auth-token-for-tests` (used in conftest.py)
- **Production Auth Token**: See `TOOLS.md` for Status Tracker API token

## Docker Notes
- **Worker changes require rebuild**: `worker.py` is baked into the image, not volume-mounted. Use `docker compose up -d --build worker` for code changes, not just restart.
- **CI Test Strategy**: UI tests (Playwright) require a running server and are ignored in CI. Only core logical/API tests run in GitHub Actions.
