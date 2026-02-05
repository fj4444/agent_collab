"""Codex CLI adapter."""
import asyncio
import shutil
from typing import AsyncIterator

from .base import AgentAdapter


class CodexAdapter(AgentAdapter):
    """Adapter for OpenAI Codex CLI."""

    async def check_available(self) -> bool:
        """Check if codex CLI is available."""
        return shutil.which("codex") is not None

    def get_cli_command(self) -> list[str]:
        """Get base CLI command."""
        return ["codex"]

    async def send(self, prompt: str) -> AsyncIterator[str]:
        """Send prompt to Codex and stream response.

        Args:
            prompt: The prompt to send.

        Yields:
            Response chunks as they arrive.
        """
        cmd = self.get_cli_command()
        cmd.extend(["--cwd", self.working_dir])

        if self._session_id:
            cmd.extend(["--session", self._session_id])

        # Create subprocess with stdin pipe
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
        """Attempt to resume a Codex session.

        Args:
            session_id: The session ID to resume.

        Returns:
            True if session exists (we assume it does for now).
        """
        # For MVP, we optimistically set the session ID
        # and let it fail gracefully if the session doesn't exist
        self._session_id = session_id
        return True
