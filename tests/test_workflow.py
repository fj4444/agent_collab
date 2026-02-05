"""Tests for workflow controller."""
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_collab.config import Config
from agent_collab.engine import Phase, WorkflowController
from agent_collab.persistence import load_state


class TestWorkflowController:
    """Tests for WorkflowController."""

    def test_init_creates_state(self):
        """Test controller creates initial state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            config.get_workdir(project_root).mkdir(parents=True, exist_ok=True)

            controller = WorkflowController(project_root, config)

            assert controller.state.phase == Phase.INIT
            assert controller.state.iteration == 0

    def test_init_loads_existing_state(self):
        """Test controller loads existing state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            # Create existing state
            state_path = config.get_state_path(project_root)
            state_path.write_text('{"phase": "review", "iteration": 2}')

            controller = WorkflowController(project_root, config)

            assert controller.state.phase == Phase.REVIEW
            assert controller.state.iteration == 2

    def test_is_approved_true(self):
        """Test is_approved returns True when approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            # Create approved comments
            comments_path = config.get_comments_path(project_root)
            comments_path.write_text("[APPROVED]\n\nLooks good!")

            controller = WorkflowController(project_root, config)

            assert controller.is_approved() is True

    def test_is_approved_false(self):
        """Test is_approved returns False when not approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            # Create non-approved comments
            comments_path = config.get_comments_path(project_root)
            comments_path.write_text("[CHANGES_REQUIRED]\n\nPlease fix X.")

            controller = WorkflowController(project_root, config)

            assert controller.is_approved() is False

    def test_is_approved_empty(self):
        """Test is_approved returns False when no comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            controller = WorkflowController(project_root, config)

            assert controller.is_approved() is False

    def test_is_max_iterations(self):
        """Test max iterations check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            config.workflow.max_iterations = 3
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            controller = WorkflowController(project_root, config)
            controller.state.iteration = 2

            assert controller.is_max_iterations() is False

            controller.state.iteration = 3
            assert controller.is_max_iterations() is True

    def test_phase_change_callback(self):
        """Test phase change triggers callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            phases_seen = []
            def on_phase_change(phase):
                phases_seen.append(phase)

            controller = WorkflowController(
                project_root, config, on_phase_change=on_phase_change
            )
            controller._set_phase(Phase.REFINE_GOAL)

            assert Phase.REFINE_GOAL in phases_seen

    def test_invalid_transition_raises(self):
        """Test invalid phase transition raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            controller = WorkflowController(project_root, config)

            with pytest.raises(ValueError, match="Invalid transition"):
                controller._set_phase(Phase.DONE)  # Can't go INIT -> DONE

    def test_get_plan_content(self):
        """Test getting plan content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            plan_path = config.get_plan_path(project_root)
            plan_path.write_text("# My Plan\n\n- Step 1")

            controller = WorkflowController(project_root, config)

            assert "My Plan" in controller.get_plan_content()

    def test_get_plan_content_empty(self):
        """Test getting plan content when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            controller = WorkflowController(project_root, config)

            assert controller.get_plan_content() == ""
