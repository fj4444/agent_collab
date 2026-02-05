"""Tests for project initialization."""
from agent_collab import main as main_module
from agent_collab.tui import AgentCollabApp


def test_import_main_module():
    """Test that main module can be imported."""
    assert hasattr(main_module, "main")


def test_import_tui_app():
    """Test that TUI app can be imported."""
    assert AgentCollabApp is not None
