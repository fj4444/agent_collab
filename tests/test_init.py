"""Tests for project initialization."""
import subprocess
import sys


def test_cli_entry_point():
    """Test that CLI entry point works."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_collab.main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "agent-collab" in result.stdout


def test_import_main_module():
    """Test that main module can be imported."""
    from agent_collab import main
    assert hasattr(main, "main")
