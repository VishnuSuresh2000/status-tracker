# AI Agent Routine - Status Tracker Project

This file contains MANDATORY instructions for any AI agent interacting with this project. All agents MUST follow these instructions without exception.

---

## 1. MANDATORY Status Tracker Rule

**ALL tasks and sub-tasks MUST be tracked using the Status Tracker.**

- **New Assignment**: Create a new task in the Status Tracker immediately upon receiving a new assignment or request from the user.
- Before starting any work, ensure the task exists in the Status Tracker.
- Break down complex work into phases and todos.
- Update task status as work progresses.
- Mark tasks as completed when done.

---

## 2. Progress Reporting

**All progress must be reported via the project's API using authentication.**

- Locate the auth token in `environment/TOOLS.md`
- Use the token to authenticate API requests
- Report task status updates, completions, and blockers via the API
- Include meaningful progress descriptions

---

## Quick Reference

- Status Tracker: Use `todoread` and `todowrite` tools
- API Auth Token: Located in `environment/TOOLS.md`
- API Base URL: `http://localhost:8000` (default)

---

**COMPLIANCE IS MANDATORY**  
*Failure to follow these instructions may result in inconsistent state and lost work.*
