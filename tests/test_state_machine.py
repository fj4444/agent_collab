"""Tests for state machine."""
import pytest

from agent_collab.engine import Phase, can_transition, get_next_phases


class TestPhase:
    """Tests for Phase enum."""

    def test_all_phases_defined(self):
        """Test all expected phases exist."""
        expected = ["init", "refine_goal", "write_plan", "review",
                    "respond", "approved", "execute", "done"]
        actual = [p.value for p in Phase]
        assert actual == expected


class TestTransitions:
    """Tests for state transitions."""

    def test_init_to_refine_goal(self):
        """Test INIT -> REFINE_GOAL is valid."""
        assert can_transition(Phase.INIT, Phase.REFINE_GOAL)

    def test_refine_goal_to_write_plan(self):
        """Test REFINE_GOAL -> WRITE_PLAN is valid."""
        assert can_transition(Phase.REFINE_GOAL, Phase.WRITE_PLAN)

    def test_write_plan_to_review(self):
        """Test WRITE_PLAN -> REVIEW is valid."""
        assert can_transition(Phase.WRITE_PLAN, Phase.REVIEW)

    def test_review_to_respond(self):
        """Test REVIEW -> RESPOND is valid."""
        assert can_transition(Phase.REVIEW, Phase.RESPOND)

    def test_review_to_approved(self):
        """Test REVIEW -> APPROVED is valid."""
        assert can_transition(Phase.REVIEW, Phase.APPROVED)

    def test_respond_to_review(self):
        """Test RESPOND -> REVIEW is valid (loop)."""
        assert can_transition(Phase.RESPOND, Phase.REVIEW)

    def test_approved_to_execute(self):
        """Test APPROVED -> EXECUTE is valid."""
        assert can_transition(Phase.APPROVED, Phase.EXECUTE)

    def test_execute_to_done(self):
        """Test EXECUTE -> DONE is valid."""
        assert can_transition(Phase.EXECUTE, Phase.DONE)

    def test_invalid_transition(self):
        """Test invalid transitions return False."""
        assert not can_transition(Phase.INIT, Phase.DONE)
        assert not can_transition(Phase.REVIEW, Phase.INIT)
        assert not can_transition(Phase.DONE, Phase.INIT)

    def test_get_next_phases(self):
        """Test getting valid next phases."""
        assert get_next_phases(Phase.REVIEW) == [Phase.RESPOND, Phase.APPROVED]
        assert get_next_phases(Phase.DONE) == []
