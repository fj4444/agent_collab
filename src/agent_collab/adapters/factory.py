"""Factory for creating agent adapters."""
from .base import AgentAdapter
from .codex import CodexAdapter
from .claude import ClaudeAdapter


def create_adapter(agent_type: str, working_dir: str) -> AgentAdapter:
    """Create an agent adapter based on type.

    Args:
        agent_type: Type of agent ("codex" or "claude").
        working_dir: Working directory for the agent.

    Returns:
        Configured AgentAdapter instance.

    Raises:
        ValueError: If agent_type is not recognized.
    """
    adapters = {
        "codex": CodexAdapter,
        "claude": ClaudeAdapter,
    }

    adapter_class = adapters.get(agent_type.lower())
    if adapter_class is None:
        raise ValueError(f"Unknown agent type: {agent_type}. Valid types: {list(adapters.keys())}")

    return adapter_class(working_dir)
