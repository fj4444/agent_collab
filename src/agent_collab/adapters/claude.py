"""Claude Code CLI adapter."""
import asyncio
import shutil
from typing import AsyncIterator

from .base import AgentAdapter


class ClaudeAdapter(AgentAdapter):
    """Adapter for Claude Code CLI."""

    async def check_available(self) -> bool:
        """Check if claude CLI is available."""
        return shutil.which("claude") is not None

    def get_cli_command(self) -> list[str]:
        """Get base CLI command."""
        return ["claude"]

    async def send(self, prompt: str) -> AsyncIterator[str]:
        """Send prompt to Claude and stream response.

        Args:
            prompt: The prompt to send.

        Yields:
            Response chunks as they arrive.
        """
        cmd = self.get_cli_command()

        # Claude uses --print for non-interactive mode
        cmd.append("--print")

        if self._session_id:
            cmd.append("--resume")

        # Create subprocess with stdin pipe
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir,
        )

        # Send prompt and close stdin
        if process.stdin:
            process.stdin.write(prompt.encode())
            await process.stdin.drain()
            process.stdin.close()

        # Stream stdout
        if process.stdout:
            while True:
                chunk = await process.stdout.read(1024)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                yield text

        await process.wait()

    async def resume_session(self, session_id: str) -> bool:
        """Attempt to resume a Claude session.

        Args:
            session_id: The session ID to resume.

        Returns:
            True if session can be resumed.
        """
        # For Claude, --resume uses the most recent session
        # We store the session_id for state tracking
        self._session_id = session_id
        return True
