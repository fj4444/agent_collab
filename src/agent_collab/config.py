"""Configuration loading and management."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclass
class RolesConfig:
    """Role to agent mapping configuration."""
    planner: str = "codex"
    reviewer: str = "claude"


@dataclass
class WorkflowConfig:
    """Workflow settings."""
    max_iterations: int = 5


@dataclass
class PathsConfig:
    """Path settings for workflow artifacts."""
    workdir: str = ".agent-collab"
    plan: str = "plan.md"
    comments: str = "comments.md"
    log: str = "log.md"


@dataclass
class Config:
    """Main configuration container."""
    roles: RolesConfig = field(default_factory=RolesConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)

    def get_workdir(self, project_root: Path) -> Path:
        """Get absolute path to workflow artifacts directory."""
        return project_root / self.paths.workdir

    def get_plan_path(self, project_root: Path) -> Path:
        """Get absolute path to plan.md."""
        return self.get_workdir(project_root) / self.paths.plan

    def get_comments_path(self, project_root: Path) -> Path:
        """Get absolute path to comments.md."""
        return self.get_workdir(project_root) / self.paths.comments

    def get_log_path(self, project_root: Path) -> Path:
        """Get absolute path to log.md."""
        return self.get_workdir(project_root) / self.paths.log

    def get_state_path(self, project_root: Path) -> Path:
        """Get absolute path to state.json."""
        return self.get_workdir(project_root) / "state.json"


def _dict_to_config(data: dict[str, Any]) -> Config:
    """Convert raw dict to Config dataclass."""
    roles_data = data.get("roles", {})
    workflow_data = data.get("workflow", {})
    paths_data = data.get("paths", {})

    return Config(
        roles=RolesConfig(
            planner=roles_data.get("planner", "codex"),
            reviewer=roles_data.get("reviewer", "claude"),
        ),
        workflow=WorkflowConfig(
            max_iterations=workflow_data.get("max_iterations", 5),
        ),
        paths=PathsConfig(
            workdir=paths_data.get("workdir", ".agent-collab"),
            plan=paths_data.get("plan", "plan.md"),
            comments=paths_data.get("comments", "comments.md"),
            log=paths_data.get("log", "log.md"),
        ),
    )


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from TOML file.

    Args:
        config_path: Path to config.toml. If None, returns default config.

    Returns:
        Config object with loaded or default values.
    """
    if config_path is None or not config_path.exists():
        return Config()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    return _dict_to_config(data)
