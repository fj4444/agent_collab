"""Agent Collab - Dual-agent collaboration workflow automation tool."""
import sys
from pathlib import Path

from .config import load_config
from .tui import AgentCollabApp


def main() -> None:
    """Entry point for agent-collab CLI."""
    # Use current directory as project root
    project_root = Path.cwd()

    # Load config from project root or use defaults
    config_path = project_root / "config.toml"
    config = load_config(config_path if config_path.exists() else None)

    # Ensure workdir exists
    workdir = config.get_workdir(project_root)
    workdir.mkdir(parents=True, exist_ok=True)

    # Run the TUI app
    app = AgentCollabApp(project_root=project_root, config=config)
    app.run()


if __name__ == "__main__":
    main()
