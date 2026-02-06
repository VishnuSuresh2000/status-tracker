# AI Agent Routine - Status Tracker Project

This file contains MANDATORY instructions for any AI agent interacting with this project. All agents MUST follow these instructions without exception.

---

## 1. MANDATORY Status Tracker Rule

**ALL tasks and sub-tasks MUST be tracked using the Status Tracker.**

- Before starting any work, create or update tasks in the Status Tracker
- Break down complex work into phases and todos
- Update task status as work progresses
- Mark tasks as completed when done

---

## 2. Startup Protocol

**Every time a session starts or the server restarts:**

1. Use the `todoread` tool to check for ongoing work in the Status Tracker
2. Review any `in_progress` or pending tasks
3. Review the current task context and history

---

## 3. Explicit Authorization

**The agent MUST ask the user for permission before continuing any ongoing work found in the tracker.**

- Do NOT automatically resume work without user confirmation
- Present the found tasks to the user
- Wait for explicit approval before proceeding

---

## 4. Progress Reporting

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
