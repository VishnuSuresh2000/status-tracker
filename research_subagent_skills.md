# OpenClaw Sub-Agent Configuration Research

## 1. Using Skills in Sub-Agents

To make a skill (like `mcporter`) available to a sub-agent, you must explicitly allow it in the global configuration (`openclaw.json`).

### Method A: Per-Agent Configuration (Recommended)
Edit `openclaw.json` to add the skill to a specific agent's `skills` list.

```json
"agents": {
  "list": [
    {
      "id": "research-panda",
      "name": "Research Panda",
      "skills": [
        "mcporter",          // <--- Add skill here
        "web_fetch",
        "brave-scraper-mcp"
      ]
      // ...
    }
  ]
}
```

### Method B: Global Sub-Agent Permission
To allow a skill for **all** spawned sub-agents (including ad-hoc ones), add it to the `tools.subagents` section:

```json
"tools": {
  "subagents": {
    "tools": {
      "alsoAllow": [
        "mcporter",          // <--- Add here to allow globally for sub-agents
        "web_fetch",
        "brave-scraper"
      ]
    }
  }
}
```

## 2. Adding "Requirements" (Environment Setup)

If "requirements" refers to system packages (like `apt` or `pip` packages) needed inside the sandbox:

### Docker Sandbox Setup
Configure the `setupCommand` in `agents.defaults.sandbox.docker`. This command runs when the sandbox container starts.

```json
"agents": {
  "defaults": {
    "sandbox": {
      "docker": {
        "setupCommand": "pip install pandas requests && apt-get update && apt-get install -y curl" 
      }
    }
  }
}
```

*Note: This applies to the shared sandbox environment used by sub-agents.*

## 3. The `mcporter` Skill Specifically

`mcporter` is a tool for managing Model Context Protocol (MCP) servers.
- **It is not "installed" by the sub-agent.** It is provided by the OpenClaw host.
- **Usage:** The sub-agent calls it directly: `mcporter list`, `mcporter call <tool>`, etc.
- **Configuration:** If the sub-agent needs to *configure* new MCP servers (e.g., "installing" a new server connection), it would use `mcporter config add ...` or `mcporter auth ...`.

## Summary Checklist
1. **Enable the skill:** Ensure `mcporter` is in `skills.entries` (enabled: true).
2. **Assign the skill:** Add "mcporter" to the agent's `skills` list or `tools.subagents.tools.alsoAllow` in `openclaw.json`.
3. **Apply Config:** Run `openclaw gateway config.apply` (or restart the gateway) to apply changes.
