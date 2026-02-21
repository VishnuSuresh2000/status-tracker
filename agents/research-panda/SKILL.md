---
name: research-panda
description: Research Panda agent with required binaries for mcporter and brave-scraper-mcp.
metadata:
  openclaw:
    requires:
      bins: ["mcporter", "brave-scraper-mcp"]
    tools:
      - name: brave_search
        server: brave-scraper
        description: Search Brave and get structured results
      - name: brave_extract
        server: brave-scraper
        description: Extract clean content from a URL
      - name: brave_scrape_page
        server: brave-scraper
        description: Scrape full page content as Markdown
---

# Research Panda Skill

This skill ensures the Research Panda agent has the necessary binaries installed to use the `mcporter` CLI and interact with the Brave Scraper MCP server.
