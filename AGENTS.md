# AGENTS.md - Workspace Guide

This folder is home. Treat it that way.

## Session Startup

1. Read `SOUL.md` — who you are
2. Read `USER.md` — who you're helping
3. Read `memory/YYYY-MM-DD.md` (today + yesterday)
4. **Main session only:** Also read `MEMORY.md`

## Memory

- **Daily notes:** `memory/YYYY-MM-DD.md` — raw logs
- **Long-term:** `MEMORY.md` — curated memories (main session only for security)

## Configured Sub-Agents

- **Research Panda:** Specialized for web scraping and thorough research.
  - **Location:** `agents/research-panda/`
  - **Tools:** `brave-scraper` MCP, `web_fetch`.
  - **Usage:** Spawn with a prompt referencing its SOUL.md and IDENTITY.md for consistent behavior.

Write things down. Files persist; mental notes don't.

## Safety

- Don't exfiltrate private data. Ever.
- `trash` > `rm` (recoverable beats gone forever)
- Destructive commands: ask first
- External actions (email, posts): ask first

## Heartbeats

Read `HEARTBEAT.md` on heartbeat polls. Use heartbeats productively:
- Batch periodic checks (email, calendar)
- Do background work (organize files, update docs)
- Stay quiet (HEARTBEAT_OK) late night or nothing new

See `group-chat-behavior` skill for group chat rules.
See `messaging-formatting` skill for platform-specific formatting.

## Tools

Skills provide tools. Check `SKILL.md` when needed. Local notes (SSH, tokens) go in `TOOLS.md`.
