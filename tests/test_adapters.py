"""Tests for agent adapters."""
import pytest

from agent_collab.adapters import (
    AgentAdapter,
    CodexAdapter,
    ClaudeAdapter,
    create_adapter,
)


class TestCodexAdapter:
    """Tests for CodexAdapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = CodexAdapter("/project")
        assert adapter.working_dir == "/project"
        assert adapter.session_id is None

    def test_get_cli_command(self):
        """Test CLI command generation."""
        adapter = CodexAdapter("/project")
        assert adapter.get_cli_command() == ["codex"]

    def test_resume_session(self):
        """Test session resume sets session ID."""
        adapter = CodexAdapter("/project")
        import asyncio
        result = asyncio.run(adapter.resume_session("test-session"))
        assert result is True
        assert adapter.session_id == "test-session"


class TestClaudeAdapter:
    """Tests for ClaudeAdapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = ClaudeAdapter("/project")
        assert adapter.working_dir == "/project"
        assert adapter.session_id is None

    def test_get_cli_command(self):
        """Test CLI command generation."""
        adapter = ClaudeAdapter("/project")
        assert adapter.get_cli_command() == ["claude"]

    def test_resume_session(self):
        """Test session resume sets session ID."""
        adapter = ClaudeAdapter("/project")
        import asyncio
        result = asyncio.run(adapter.resume_session("test-session"))
        assert result is True
        assert adapter.session_id == "test-session"


class TestAdapterFactory:
    """Tests for adapter factory."""

    def test_create_codex_adapter(self):
        """Test creating Codex adapter."""
        adapter = create_adapter("codex", "/project")
        assert isinstance(adapter, CodexAdapter)
        assert adapter.working_dir == "/project"

    def test_create_claude_adapter(self):
        """Test creating Claude adapter."""
        adapter = create_adapter("claude", "/project")
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.working_dir == "/project"

    def test_create_adapter_case_insensitive(self):
        """Test factory is case insensitive."""
        adapter1 = create_adapter("CODEX", "/project")
        adapter2 = create_adapter("Claude", "/project")
        assert isinstance(adapter1, CodexAdapter)
        assert isinstance(adapter2, ClaudeAdapter)

    def test_create_adapter_unknown_type(self):
        """Test factory raises for unknown type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            create_adapter("unknown", "/project")


class TestAdapterInterface:
    """Tests for adapter interface compliance."""

    def test_codex_is_agent_adapter(self):
        """Test CodexAdapter implements AgentAdapter."""
        adapter = CodexAdapter("/project")
        assert isinstance(adapter, AgentAdapter)

    def test_claude_is_agent_adapter(self):
        """Test ClaudeAdapter implements AgentAdapter."""
        adapter = ClaudeAdapter("/project")
        assert isinstance(adapter, AgentAdapter)
