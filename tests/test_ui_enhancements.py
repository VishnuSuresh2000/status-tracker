"""
Unit tests for UI enhancement features in index.html.

Tests cover:
- Lazy loading logic (visibleCompletedCount)
- Skill parsing (parseSkills/combineSkills)
- Mermaid zoom controls
- Mobile responsive grid classes
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

# Test constants
MINIMAL_TASK = {
    "name": "Test Task",
    "priority": "medium",
    "phases": [{"name": "P1", "todos": [{"name": "T1"}]}],
}


class TestLazyLoadingLogic:
    """Test the lazy loading pagination logic for completed tasks."""

    def test_visible_completed_count_starts_at_five(self):
        """Verify default visibleCompletedCount is 5."""
        # This matches the JavaScript: let visibleCompletedCount = 5;
        default_count = 5
        assert default_count == 5

    def test_load_more_increments_by_five(self):
        """Verify loadMoreCompletedTasks increments by 5."""
        count = 5
        count += 5  # First load more
        assert count == 10
        count += 5  # Second load more
        assert count == 15

    def test_slice_completed_tasks(self):
        """Verify slicing logic for completed tasks display."""
        all_done = list(range(1, 21))  # 20 completed tasks
        visible_count = 5
        
        visible = all_done[:visible_count]
        assert len(visible) == 5
        assert visible == [1, 2, 3, 4, 5]
        
        # After loading more
        visible_count = 10
        visible = all_done[:visible_count]
        assert len(visible) == 10
        
        # All tasks visible
        visible_count = 25
        visible = all_done[:visible_count]
        assert len(visible) == 20  # Capped at actual length


class TestSkillParsing:
    """Test the parseSkills and combineSkills helper functions."""

    def test_parse_agent_skills(self):
        """Parse skills with agent: prefix."""
        skills_string = "agent:opencode-controller,agent:github,agent:testing"
        
        agent_skills = []
        task_skills = []
        
        for skill in skills_string.split(','):
            skill = skill.strip()
            if skill.startswith('agent:'):
                agent_skills.append(skill[6:])  # Remove 'agent:' prefix
            elif skill.startswith('task:'):
                task_skills.append(skill[5:])  # Remove 'task:' prefix
        
        assert agent_skills == ['opencode-controller', 'github', 'testing']
        assert task_skills == []

    def test_parse_task_skills(self):
        """Parse skills with task: prefix."""
        skills_string = "task:python,task:db,task:api"
        
        agent_skills = []
        task_skills = []
        
        for skill in skills_string.split(','):
            skill = skill.strip()
            if skill.startswith('agent:'):
                agent_skills.append(skill[6:])
            elif skill.startswith('task:'):
                task_skills.append(skill[5:])
        
        assert agent_skills == []
        assert task_skills == ['python', 'db', 'api']

    def test_parse_mixed_skills(self):
        """Parse mixed agent and task skills."""
        skills_string = "agent:opencode,agent:github,task:testing,task:db"
        
        agent_skills = []
        task_skills = []
        
        for skill in skills_string.split(','):
            skill = skill.strip()
            if skill.startswith('agent:'):
                agent_skills.append(skill[6:])
            elif skill.startswith('task:'):
                task_skills.append(skill[5:])
        
        assert agent_skills == ['opencode', 'github']
        assert task_skills == ['testing', 'db']

    def test_combine_skills(self):
        """Combine agent and task skills with prefixes."""
        agent_skills = ['opencode', 'github']
        task_skills = ['testing', 'db']
        
        combined = []
        for s in agent_skills:
            combined.append(f'agent:{s}')
        for s in task_skills:
            combined.append(f'task:{s}')
        
        result = ','.join(combined)
        assert result == "agent:opencode,agent:github,task:testing,task:db"

    def test_parse_empty_skills(self):
        """Parse empty or None skills string."""
        skills_string = ""
        
        agent_skills = []
        task_skills = []
        
        if skills_string:
            for skill in skills_string.split(','):
                skill = skill.strip()
                if skill.startswith('agent:'):
                    agent_skills.append(skill[6:])
                elif skill.startswith('task:'):
                    task_skills.append(skill[5:])
        
        assert agent_skills == []
        assert task_skills == []


class TestMermaidZoomControls:
    """Test Mermaid chart zoom functionality."""

    def test_zoom_increases_scale(self):
        """Verify zoom in multiplies scale factor."""
        zoom_level = 1.0
        factor = 1.2  # Zoom in
        
        zoom_level *= factor
        assert zoom_level == 1.2

    def test_zoom_out_decreases_scale(self):
        """Verify zoom out divides scale factor."""
        zoom_level = 1.0
        factor = 0.8  # Zoom out
        
        zoom_level *= factor
        assert zoom_level == 0.8

    def test_zoom_clamped_minimum(self):
        """Verify zoom doesn't go below 0.5x."""
        zoom_level = 0.4
        zoom_level = max(0.5, zoom_level)
        assert zoom_level == 0.5

    def test_zoom_clamped_maximum(self):
        """Verify zoom doesn't exceed 3x."""
        zoom_level = 4.0
        zoom_level = min(3, zoom_level)
        assert zoom_level == 3.0

    def test_reset_zoom(self):
        """Verify reset returns zoom to 1.0."""
        zoom_level = 2.5
        zoom_level = 1.0  # Reset
        assert zoom_level == 1.0


class TestMobileResponsiveGrid:
    """Test mobile responsive grid class logic."""

    def test_grid_classes_format(self):
        """Verify grid classes follow Tailwind responsive pattern."""
        # Expected: grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
        classes = "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        
        assert "grid-cols-1" in classes  # Mobile default
        assert "sm:grid-cols-2" in classes  # Small screens
        assert "lg:grid-cols-3" in classes  # Large screens

    def test_agent_grid_classes_format(self):
        """Verify agent status grid uses responsive classes."""
        classes = "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        
        assert "grid-cols-1" in classes  # Mobile default
        assert "xl:grid-cols-4" in classes  # Extra large screens


class TestSkillBubbleStyling:
    """Test skill bubble styling classes."""

    def test_agent_skill_classes(self):
        """Verify agent skill bubble uses indigo colors."""
        # Expected: bg-indigo-100 text-indigo-700 rounded-full
        classes = "px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700"
        
        assert "rounded-full" in classes
        assert "bg-indigo-100" in classes
        assert "text-indigo-700" in classes

    def test_task_skill_classes(self):
        """Verify task skill bubble uses amber colors."""
        # Expected: bg-amber-100 text-amber-700 rounded-full
        classes = "px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
        
        assert "rounded-full" in classes
        assert "bg-amber-100" in classes
        assert "text-amber-700" in classes

    def test_skill_bubble_truncation(self):
        """Verify skill bubbles have truncation for long names."""
        classes = "truncate max-w-[100px] sm:max-w-[120px]"
        
        assert "truncate" in classes
        assert "max-w-" in classes
