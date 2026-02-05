"""Workflow state machine."""
from enum import Enum


class Phase(Enum):
    """Workflow phases."""
    INIT = "init"
    REFINE_GOAL = "refine_goal"
    WRITE_PLAN = "write_plan"
    REVIEW = "review"
    RESPOND = "respond"
    APPROVED = "approved"
    EXECUTE = "execute"
    DONE = "done"


# Valid state transitions
TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.INIT: [Phase.REFINE_GOAL],
    Phase.REFINE_GOAL: [Phase.WRITE_PLAN],
    Phase.WRITE_PLAN: [Phase.REVIEW],
    Phase.REVIEW: [Phase.RESPOND, Phase.APPROVED],
    Phase.RESPOND: [Phase.REVIEW],
    Phase.APPROVED: [Phase.EXECUTE],
    Phase.EXECUTE: [Phase.DONE, Phase.EXECUTE],  # Can loop for multiple steps
    Phase.DONE: [],
}


def can_transition(current: Phase, target: Phase) -> bool:
    """Check if transition from current to target phase is valid.

    Args:
        current: Current phase.
        target: Target phase.

    Returns:
        True if transition is valid.
    """
    return target in TRANSITIONS.get(current, [])


def get_next_phases(current: Phase) -> list[Phase]:
    """Get list of valid next phases from current phase.

    Args:
        current: Current phase.

    Returns:
        List of valid next phases.
    """
    return TRANSITIONS.get(current, [])
