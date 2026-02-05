"""Abstract base class for agent adapters."""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class AgentAdapter(ABC):
    """Abstract base class for CLI agent adapters."""

    def __init__(self, working_dir: str):
        """Initialize adapter with working directory.

        Args:
            working_dir: The project root directory where agent should execute.
        """
        self.working_dir = working_dir
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        """Get current session ID."""
        return self._session_id

    @abstractmethod
    async def send(self, prompt: str) -> AsyncIterator[str]:
        """Send prompt to agent and stream response.

        Args:
            prompt: The prompt to send to the agent.

        Yields:
            Response chunks as they arrive.
        """
        pass

    @abstractmethod
    async def resume_session(self, session_id: str) -> bool:
        """Attempt to resume a previous session.

        Args:
            session_id: The session ID to resume.

        Returns:
            True if session was successfully resumed, False otherwise.
        """
        pass

    @abstractmethod
    def get_cli_command(self) -> list[str]:
        """Get the base CLI command for this agent.

        Returns:
            List of command parts (e.g., ["codex"] or ["claude"]).
        """
        pass

    @abstractmethod
    async def check_available(self) -> bool:
        """Check if the agent CLI is available.

        Returns:
            True if CLI is installed and accessible.
        """
        pass
