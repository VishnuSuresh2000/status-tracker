# MEMORY.md - Preferences & Configuration

## Mandatory Rules

- **Status Tracker:** Use for every task with phases/todos. Report via API using auth token in TOOLS.md.
- **Coding Tool:** Use `opencode-controller` skill for all coding, editing, debugging. Primary tool.

## Personal Information

- **Ruto's Email:** rutoassistant@gmail.com (for gog CLI auth)

## Configuration Notes

- **Heartbeat Interval:** 2 hours (`agents.defaults.heartbeat.every: "2h"`)
- **Note:** Config changes/hot reloads reset the heartbeat timer, causing it to fire sooner than scheduled
- **Test Auth Token:** `test-auth-token-for-tests` (conftest.py)
- **Production Auth Token:** See TOOLS.md
- **Sandbox Network:** `agents.defaults.sandbox.docker.network = "traefik"` (2026-02-10) — allows sub-agents to access Docker services (e.g., `http://status-tracker-app:8000`)

## Docker Notes

- **Worker changes require rebuild:** `worker.py` is baked into image. Use `docker compose up -d --build worker` for code changes.
- **CI Test Strategy:** UI tests (Playwright) need running server, ignored in CI. Only core API tests run in GitHub Actions.

## Project References

- **Status Tracker History:** See `status-tracker/HISTORY.md` for development phases
- **Brave Scraper MCP:** See project README for status
