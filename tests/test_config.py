"""Tests for configuration loading."""
from pathlib import Path
import tempfile

from agent_collab.config import (
    Config,
    RolesConfig,
    WorkflowConfig,
    PathsConfig,
    load_config,
)


def test_default_config():
    """Test that default config has expected values."""
    config = Config()
    assert config.roles.planner == "codex"
    assert config.roles.reviewer == "claude"
    assert config.workflow.max_iterations == 5
    assert config.paths.workdir == ".agent-collab"


def test_load_config_nonexistent_file():
    """Test loading config from nonexistent file returns defaults."""
    config = load_config(Path("/nonexistent/config.toml"))
    assert config.roles.planner == "codex"


def test_load_config_none_path():
    """Test loading config with None path returns defaults."""
    config = load_config(None)
    assert config.roles.planner == "codex"


def test_load_config_from_file():
    """Test loading config from actual TOML file."""
    toml_content = """
[roles]
planner = "claude"
reviewer = "codex"

[workflow]
max_iterations = 10

[paths]
workdir = "custom-dir"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        f.flush()
        config = load_config(Path(f.name))

    assert config.roles.planner == "claude"
    assert config.roles.reviewer == "codex"
    assert config.workflow.max_iterations == 10
    assert config.paths.workdir == "custom-dir"


def test_config_path_helpers():
    """Test path helper methods."""
    config = Config()
    project_root = Path("/project")

    assert config.get_workdir(project_root) == Path("/project/.agent-collab")
    assert config.get_plan_path(project_root) == Path("/project/.agent-collab/plan.md")
    assert config.get_comments_path(project_root) == Path("/project/.agent-collab/comments.md")
    assert config.get_state_path(project_root) == Path("/project/.agent-collab/state.json")


def test_partial_config_uses_defaults():
    """Test that partial config fills in defaults."""
    toml_content = """
[roles]
planner = "claude"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        f.flush()
        config = load_config(Path(f.name))

    assert config.roles.planner == "claude"
    assert config.roles.reviewer == "claude"  # default
    assert config.workflow.max_iterations == 5  # default
