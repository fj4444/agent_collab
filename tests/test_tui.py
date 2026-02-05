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
            app = AgentCollabApp(project_root=project_root)

            assert app.project_root == project_root
            assert app.config is not None
            assert app.state.phase == Phase.INIT

    def test_app_with_custom_config(self):
        """Test app with custom config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            config.workflow.max_iterations = 10

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

            assert app.state.phase == Phase.REVIEW
            assert app.state.iteration == 3

    def test_app_bindings(self):
        """Test app has expected key bindings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app = AgentCollabApp(project_root=Path(tmpdir))

            binding_keys = [b.key for b in app.BINDINGS]
            assert "q" in binding_keys
            assert "enter" in binding_keys
            assert "r" in binding_keys


class TestAppMethods:
    """Tests for app methods."""

    def test_set_phase(self):
        """Test setting phase updates state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            config = Config()
            workdir = config.get_workdir(project_root)
            workdir.mkdir(parents=True, exist_ok=True)

            app = AgentCollabApp(project_root=project_root, config=config)
            app.set_phase(Phase.REFINE_GOAL)

            assert app.state.phase == Phase.REFINE_GOAL

            # Check state was persisted
            from agent_collab.persistence import load_state
            loaded = load_state(config.get_state_path(project_root))
            assert loaded is not None
            assert loaded.phase == Phase.REFINE_GOAL
