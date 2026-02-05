"""Workflow state persistence."""
import json
import os
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from ..engine.state_machine import Phase


@dataclass
class WorkflowState:
    """Persistent workflow state."""
    phase: Phase
    iteration: int = 0
    planner_session: str | None = None
    reviewer_session: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "phase": self.phase.value,
            "iteration": self.iteration,
            "planner_session": self.planner_session,
            "reviewer_session": self.reviewer_session,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowState":
        """Create from dictionary."""
        return cls(
            phase=Phase(data["phase"]),
            iteration=data.get("iteration", 0),
            planner_session=data.get("planner_session"),
            reviewer_session=data.get("reviewer_session"),
        )


def save_state(state: WorkflowState, path: Path) -> None:
    """Save workflow state to JSON file.

    Uses atomic write (write to temp file, then rename) to prevent corruption.

    Args:
        state: The workflow state to save.
        path: Path to state.json file.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file first, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".state_",
        suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
        os.rename(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_state(path: Path) -> WorkflowState | None:
    """Load workflow state from JSON file.

    Args:
        path: Path to state.json file.

    Returns:
        WorkflowState if file exists and is valid, None otherwise.
    """
    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        return WorkflowState.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def delete_state(path: Path) -> None:
    """Delete state file if it exists.

    Args:
        path: Path to state.json file.
    """
    if path.exists():
        path.unlink()


def state_exists(path: Path) -> bool:
    """Check if state file exists.

    Args:
        path: Path to state.json file.

    Returns:
        True if state file exists.
    """
    return path.exists()
