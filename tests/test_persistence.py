"""Tests for state persistence."""
import tempfile
from pathlib import Path

from agent_collab.engine import Phase
from agent_collab.persistence import (
    WorkflowState,
    save_state,
    load_state,
    delete_state,
    state_exists,
)


class TestWorkflowState:
    """Tests for WorkflowState dataclass."""

    def test_default_values(self):
        """Test default values."""
        state = WorkflowState(phase=Phase.INIT)
        assert state.phase == Phase.INIT
        assert state.iteration == 0
        assert state.planner_session is None
        assert state.reviewer_session is None

    def test_to_dict(self):
        """Test conversion to dict."""
        state = WorkflowState(
            phase=Phase.REVIEW,
            iteration=3,
            planner_session="session-123",
            reviewer_session="session-456",
        )
        d = state.to_dict()
        assert d["phase"] == "review"
        assert d["iteration"] == 3
        assert d["planner_session"] == "session-123"
        assert d["reviewer_session"] == "session-456"

    def test_from_dict(self):
        """Test creation from dict."""
        d = {
            "phase": "execute",
            "iteration": 5,
            "planner_session": "p-session",
            "reviewer_session": None,
        }
        state = WorkflowState.from_dict(d)
        assert state.phase == Phase.EXECUTE
        assert state.iteration == 5
        assert state.planner_session == "p-session"
        assert state.reviewer_session is None


class TestPersistence:
    """Tests for save/load functions."""

    def test_save_and_load(self):
        """Test save then load round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".agent-collab" / "state.json"

            state = WorkflowState(
                phase=Phase.REVIEW,
                iteration=2,
                planner_session="planner-123",
            )
            save_state(state, path)
            loaded = load_state(path)

            assert loaded is not None
            assert loaded.phase == Phase.REVIEW
            assert loaded.iteration == 2
            assert loaded.planner_session == "planner-123"

    def test_load_nonexistent(self):
        """Test loading from nonexistent file returns None."""
        result = load_state(Path("/nonexistent/state.json"))
        assert result is None

    def test_load_invalid_json(self):
        """Test loading invalid JSON returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()
            result = load_state(Path(f.name))
        assert result is None

    def test_state_exists(self):
        """Test state_exists function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"

            assert not state_exists(path)

            state = WorkflowState(phase=Phase.INIT)
            save_state(state, path)

            assert state_exists(path)

    def test_delete_state(self):
        """Test deleting state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"

            state = WorkflowState(phase=Phase.INIT)
            save_state(state, path)
            assert state_exists(path)

            delete_state(path)
            assert not state_exists(path)

    def test_delete_nonexistent_state(self):
        """Test deleting nonexistent state doesn't error."""
        delete_state(Path("/nonexistent/state.json"))  # Should not raise
