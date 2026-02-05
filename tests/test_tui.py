"""Tests for TUI application."""
import tempfile
from pathlib import Path

import pytest

from agent_collab.config import Config
from agent_collab.engine import Phase
from agent_collab.tui import AgentCollabApp


class TestAgentCollabApp:
    """Tests for main TUI application."""

    def test_app_init(self):
        """Test app initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # Create workdir
            (project_root / ".agent-collab").mkdir()

            app = AgentCollabApp(project_root=project_root)

            assert app.project_root == project_root
            assert app.config is not None
            assert app.workflow is not None
            assert app.workflow.state.phase == Phase.INIT

    def test_app_with_custom_config(self):
        """Test app with custom config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            config.workflow.max_iterations = 10
            config.get_workdir(project_root).mkdir(parents=True, exist_ok=True)

            app = AgentCollabApp(project_root=project_root, config=config)

            assert app.config.workflow.max_iterations == 10

    def test_app_loads_existing_state(self):
        """Test app loads existing state from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()

            # Create state file
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)
            state_path = config.get_state_path(project_root)
            state_path.write_text('{"phase": "review", "iteration": 3}')

            app = AgentCollabApp(project_root=project_root, config=config)

            assert app.workflow.state.phase == Phase.REVIEW
            assert app.workflow.state.iteration == 3

    def test_app_bindings(self):
        """Test app has expected key bindings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".agent-collab").mkdir()

            app = AgentCollabApp(project_root=project_root)

            binding_keys = [b.key for b in app.BINDINGS]
            assert "q" in binding_keys
            assert "r" in binding_keys


class TestAppWorkflow:
    """Tests for app workflow integration."""

    def test_workflow_controller_created(self):
        """Test workflow controller is created on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".agent-collab").mkdir()

            app = AgentCollabApp(project_root=project_root)

            assert app.workflow is not None
            assert app.workflow.project_root == project_root
