"""Unit tests for new Brave Scraper MCP features and validation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.server import BraveScraperServer
from mcp.types import TextContent

@pytest.fixture
def server():
    """Create a server instance with mocked components."""
    with patch('src.server.BrowserManager'):
        server = BraveScraperServer()
        server.browser_manager = MagicMock()
        server.browser_manager.page = AsyncMock()
        server.browser_manager.subagent_manager = None
        return server

@pytest.mark.asyncio
async def test_brave_scrape_page_routing_isolated(server):
    """Verify brave_scrape_page tool calls the correct internal method."""
    with patch('src.server.BraveSearchTools') as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.scrape_page = AsyncMock(return_value="# Markdown Result")
        
        # Mock isolated_context
        mock_page = AsyncMock()
        server.browser_manager.isolated_context.return_value.__aenter__.return_value = mock_page
        
        args = {"url": "https://example.com", "include_images": True}
        result = await server._execute_tool_isolated("brave_scrape_page", args)
        
        mock_instance.scrape_page.assert_called_once_with(
            url="https://example.com", 
            include_images=True
        )
        assert result == "# Markdown Result"

@pytest.mark.asyncio
async def test_brave_scrape_page_routing_shared(server):
    """Verify brave_scrape_page tool calls the correct internal method in shared context."""
    with patch('src.server.BraveSearchTools') as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.scrape_page = AsyncMock(return_value="# Markdown Result")
        
        args = {"url": "https://example.com", "include_images": False}
        result = await server._execute_tool("brave_scrape_page", args)
        
        mock_instance.scrape_page.assert_called_once_with(
            url="https://example.com", 
            include_images=False
        )
        assert result == "# Markdown Result"

@pytest.mark.asyncio
async def test_schema_enforcement_definitions(server):
    """Verify that tool schemas have the new validation constraints."""
    # The server registers tools via a handler. We can manually call it.
    # The list_tools handler is registered in _setup_handlers.
    # It's an internal function, but it's registered on the server.server (mcp.Server).
    
    # We can trigger the get_tools method on the mcp server
    tools = await server.server.get_tools()
    
    # Verify brave_search schema
    search_tool = next(t for t in tools if t.name == "brave_search")
    search_schema = search_tool.inputSchema
    assert search_schema["properties"]["query"]["minLength"] == 1
    assert search_schema["additionalProperties"] is False
    assert search_schema["properties"]["count"]["minimum"] == 1
    assert search_schema["properties"]["count"]["maximum"] == 20
    
    # Verify brave_scrape_page schema
    scrape_tool = next(t for t in tools if t.name == "brave_scrape_page")
    scrape_schema = scrape_tool.inputSchema
    assert scrape_schema["properties"]["url"]["minLength"] == 1
    assert scrape_schema["additionalProperties"] is False
    assert "include_images" in scrape_schema["properties"]

@pytest.mark.asyncio
async def test_brave_search_logic_validation():
    """Verify that BraveSearchTools.search raises error for empty query."""
    from src.tools.brave_search import BraveSearchTools
    mock_page = AsyncMock()
    tools = BraveSearchTools(mock_page)
    
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await tools.search(query="")
    
    with pytest.raises(ValueError, match="Query cannot be empty"):
        await tools.search(query="   ")

@pytest.mark.asyncio
async def test_brave_scrape_page_convenience():
    """Verify the convenience function in brave_search.py."""
    from src.tools.brave_search import brave_scrape_page
    mock_page = AsyncMock()
    
    with patch('src.tools.brave_search.BraveSearchTools') as MockTools:
        mock_instance = MockTools.return_value
        mock_instance.scrape_page = AsyncMock(return_value="# Success")
        
        res = await brave_scrape_page(mock_page, "https://example.com", include_images=True)
        mock_instance.scrape_page.assert_called_once_with("https://example.com", True)
        assert res == "# Success"
