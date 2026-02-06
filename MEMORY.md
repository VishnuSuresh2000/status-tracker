- **Status Tracker Rule:** MANDATORY to use Status Tracker for every task.
- **On Startup:** Must check Status Tracker for ongoing work and ask user if I can continue.
- **Task Management:** Report progress via API using the auth token in `TOOLS.md`.

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

**Phase 5 In Progress:**
- 🛠️ Project Update & GitHub Sync (Task ID 5).
- 🛠️ Ping Indicator Feature (Completed, added to dashboard).



## Opencode Controller Usage
- Start Opencode with model: `/home/node/.openclaw/workspace/node_modules/opencode-linux-x64/bin/opencode run --model opencode/kimi-k2.5-free`
- Use `/sessions` for session management
- Use `/agents` to switch between Plan and Build modes
- Use `/models` for model selection
- Follow Plan → Build workflow loop for coding tasks