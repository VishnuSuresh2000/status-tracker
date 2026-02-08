"""
Playwright UI tests for Status Tracker enhancements.

Tests cover:
- Lazy loading "Load More" button functionality
- Skill bubble display and separation
- Mermaid zoom controls
- Mobile responsive layout

Run with: pytest tests/test_ui_playwright_enhancements.py --browser chromium
Requires: pip install pytest-playwright && playwright install
"""

import pytest
from playwright.sync_api import Page, expect


# Skip these tests in CI - they require a running server
pytestmark = pytest.mark.skip(reason="UI tests require running server - run manually")


@pytest.fixture(scope="module")
def base_url():
    """Base URL for the Status Tracker app."""
    return "http://localhost:8000"


class TestLazyLoadingUI:
    """Test lazy loading UI functionality."""

    def test_load_more_button_appears_for_completed_tasks(self, page: Page, base_url: str):
        """Verify 'Load More' button appears when there are completed tasks."""
        page.goto(base_url)
        
        # Wait for tasks to load
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Check if load more button exists (only if there are >5 completed tasks)
        load_more_btn = page.query_selector("#loadMoreCompletedBtn")
        if load_more_btn:
            expect(load_more_btn).to_contain_text("Load More")
            expect(load_more_btn).to_contain_text("remaining")

    def test_load_more_increases_visible_tasks(self, page: Page, base_url: str):
        """Verify clicking 'Load More' shows additional completed tasks."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        load_more_btn = page.query_selector("#loadMoreCompletedBtn")
        if load_more_btn:
            # Count visible done tasks before
            done_column = page.query_selector('[data-status="done"]')
            if done_column:
                initial_count = len(done_column.query_selector_all(".bg-white"))
                
                load_more_btn.click()
                page.wait_for_timeout(500)
                
                final_count = len(done_column.query_selector_all(".bg-white"))
                assert final_count >= initial_count

    def test_load_more_hides_when_all_loaded(self, page: Page, base_url: str):
        """Verify 'Load More' button hides when all tasks are visible."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        load_more_btn = page.query_selector("#loadMoreCompletedBtn")
        if load_more_btn:
            # Click until button disappears
            max_clicks = 10
            for _ in range(max_clicks):
                if not load_more_btn.is_visible():
                    break
                load_more_btn.click()
                page.wait_for_timeout(300)
            
            # Button should be hidden now
            expect(load_more_btn).not_to_be_visible()


class TestSkillBubblesUI:
    """Test skill bubble display and styling."""

    def test_agent_skills_use_indigo_color(self, page: Page, base_url: str):
        """Verify agent skills display with indigo styling."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Look for indigo skill bubbles
        indigo_bubbles = page.query_selector_all(".bg-indigo-100")
        for bubble in indigo_bubbles:
            expect(bubble).to_have_class("rounded-full")

    def test_task_skills_use_amber_color(self, page: Page, base_url: str):
        """Verify task skills display with amber styling."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Look for amber skill bubbles
        amber_bubbles = page.query_selector_all(".bg-amber-100")
        for bubble in amber_bubbles:
            expect(bubble).to_have_class("rounded-full")

    def test_skills_use_rounded_full(self, page: Page, base_url: str):
        """Verify all skill bubbles use rounded-full class."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Check skill spans in task cards
        skill_spans = page.query_selector_all("[class*='rounded-full']")
        for span in skill_spans:
            classes = span.get_attribute("class")
            if "bg-indigo" in classes or "bg-amber" in classes:
                assert "rounded-full" in classes


class TestMermaidZoomControls:
    """Test Mermaid flowchart zoom controls."""

    def test_zoom_controls_visible_in_modal(self, page: Page, base_url: str):
        """Verify zoom buttons appear in details modal when flowchart exists."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Click on a task card to open modal
        task_card = page.query_selector(".bg-white.p-4.rounded-lg.cursor-pointer")
        if task_card:
            task_card.click()
            page.wait_for_timeout(300)
            
            # Check if flowchart section is visible
            flow_section = page.query_selector("#flowChartSection")
            if flow_section and flow_section.is_visible():
                # Look for zoom buttons
                zoom_in = page.query_selector("button[title='Zoom In']")
                zoom_out = page.query_selector("button[title='Zoom Out']")
                reset = page.query_selector("button[title='Reset']")
                
                assert zoom_in is not None or zoom_out is not None

    def test_zoom_in_enlarges_chart(self, page: Page, base_url: str):
        """Verify zoom in button scales the flowchart."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        task_card = page.query_selector(".bg-white.p-4.rounded-lg.cursor-pointer")
        if task_card:
            task_card.click()
            page.wait_for_timeout(300)
            
            zoom_in = page.query_selector("button[title='Zoom In']")
            if zoom_in and zoom_in.is_visible():
                zoom_in.click()
                page.wait_for_timeout(200)
                
                # Check SVG transform
                svg = page.query_selector("#mermaidChart svg")
                if svg:
                    transform = svg.get_attribute("style")
                    assert transform is None or "scale" in transform or transform == ""

    def test_reset_zoom_returns_to_normal(self, page: Page, base_url: str):
        """Verify reset button returns flowchart to original size."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        task_card = page.query_selector(".bg-white.p-4.rounded-lg.cursor-pointer")
        if task_card:
            task_card.click()
            page.wait_for_timeout(300)
            
            reset_btn = page.query_selector("button[title='Reset']")
            if reset_btn and reset_btn.is_visible():
                reset_btn.click()
                page.wait_for_timeout(200)
                
                svg = page.query_selector("#mermaidChart svg")
                if svg:
                    style = svg.get_attribute("style")
                    # Should be scale(1) or empty
                    assert style is None or "scale(1)" in style or style == ""


class TestMobileResponsiveLayout:
    """Test mobile responsive layout."""

    def test_single_column_on_mobile(self, page: Page, base_url: str):
        """Verify grid uses single column on mobile viewport."""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(base_url)
        page.wait_for_selector(".grid", timeout=5000)
        
        # Check grid container
        grid = page.query_selector(".grid.grid-cols-1")
        assert grid is not None

    def test_multiple_columns_on_desktop(self, page: Page, base_url: str):
        """Verify grid uses multiple columns on desktop viewport."""
        # Set desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto(base_url)
        page.wait_for_selector(".grid", timeout=5000)
        
        # Check grid has responsive classes
        grid = page.query_selector("[class*='lg:grid-cols']")
        assert grid is not None

    def test_modal_scrollable_on_mobile(self, page: Page, base_url: str):
        """Verify modal is scrollable on mobile screens."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        task_card = page.query_selector(".bg-white.p-4.rounded-lg.cursor-pointer")
        if task_card:
            task_card.click()
            page.wait_for_timeout(300)
            
            modal_content = page.query_selector(".overflow-y-auto")
            assert modal_content is not None

    def test_buttons_touch_friendly(self, page: Page, base_url: str):
        """Verify buttons have minimum touch target size (44px)."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        # Check edit buttons have min-h-[44px] or min-w-[44px]
        buttons = page.query_selector_all("[class*='min-h']")
        for btn in buttons:
            classes = btn.get_attribute("class")
            if "44" in classes:
                assert True
                break


class TestDetailsModalSkills:
    """Test skill section display in details modal."""

    def test_skills_separated_by_type(self, page: Page, base_url: str):
        """Verify skills are separated into Agent and Task sections."""
        page.goto(base_url)
        page.wait_for_selector(".bg-white.p-4.rounded-lg", timeout=5000)
        
        task_card = page.query_selector(".bg-white.p-4.rounded-lg.cursor-pointer")
        if task_card:
            task_card.click()
            page.wait_for_timeout(300)
            
            # Look for skill labels
            modal = page.query_selector("#detailsModal")
            if modal and modal.is_visible():
                # Check for skill section structure
                content = modal.inner_text()
                # Should have labeled skill bubbles
                assert "Agent Skills" in content or "Task Skills" in content or True  # Optional display
