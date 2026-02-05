"""TUI application for agent-collab."""
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Header, TabbedContent, TabPane, TextArea, Static

from ..config import Config, load_config
from ..engine import Phase
from ..persistence import WorkflowState, load_state, save_state


class ConversationTab(Static):
    """Tab for conversation with agents."""

    def compose(self) -> ComposeResult:
        yield TextArea(id="conversation", read_only=True)


class PlanTab(Static):
    """Tab for displaying plan.md content."""

    def __init__(self, plan_path: Path) -> None:
        super().__init__()
        self.plan_path = plan_path

    def compose(self) -> ComposeResult:
        yield TextArea(id="plan-content", read_only=True)

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        """Refresh plan content from file."""
        text_area = self.query_one("#plan-content", TextArea)
        if self.plan_path.exists():
            text_area.load_text(self.plan_path.read_text())
        else:
            text_area.load_text("(No plan yet)")


class CommentsTab(Static):
    """Tab for displaying comments.md content."""

    def __init__(self, comments_path: Path) -> None:
        super().__init__()
        self.comments_path = comments_path

    def compose(self) -> ComposeResult:
        yield TextArea(id="comments-content", read_only=True)

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        """Refresh comments content from file."""
        text_area = self.query_one("#comments-content", TextArea)
        if self.comments_path.exists():
            text_area.load_text(self.comments_path.read_text())
        else:
            text_area.load_text("(No comments yet)")


class StatusBar(Static):
    """Status bar showing current workflow phase."""

    def __init__(self, phase: Phase) -> None:
        super().__init__()
        self.phase = phase

    def compose(self) -> ComposeResult:
        yield Static(f"Phase: {self.phase.value}", id="phase-display")

    def update_phase(self, phase: Phase) -> None:
        """Update displayed phase."""
        self.phase = phase
        display = self.query_one("#phase-display", Static)
        display.update(f"Phase: {phase.value}")


class AgentCollabApp(App):
    """Main TUI application."""

    CSS = """
    #conversation, #plan-content, #comments-content {
        height: 100%;
        width: 100%;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    #phase-display {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "proceed", "Proceed"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        project_root: Path,
        config: Config | None = None,
    ) -> None:
        super().__init__()
        self.project_root = project_root
        self.config = config or load_config()
        self.state = self._load_or_init_state()

    def _load_or_init_state(self) -> WorkflowState:
        """Load existing state or create new one."""
        state_path = self.config.get_state_path(self.project_root)
        state = load_state(state_path)
        if state is None:
            state = WorkflowState(phase=Phase.INIT)
        return state

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Conversation", id="tab-conversation"):
                yield ConversationTab()
            with TabPane("Plan", id="tab-plan"):
                yield PlanTab(self.config.get_plan_path(self.project_root))
            with TabPane("Comments", id="tab-comments"):
                yield CommentsTab(self.config.get_comments_path(self.project_root))
        yield StatusBar(self.state.phase)
        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_proceed(self) -> None:
        """Proceed to next step (placeholder)."""
        self.notify("Proceed action triggered")

    def action_refresh(self) -> None:
        """Refresh file contents."""
        try:
            plan_tab = self.query_one(PlanTab)
            plan_tab.refresh_content()
        except Exception:
            pass

        try:
            comments_tab = self.query_one(CommentsTab)
            comments_tab.refresh_content()
        except Exception:
            pass

        self.notify("Content refreshed")

    def update_conversation(self, text: str) -> None:
        """Add text to conversation area."""
        try:
            conv = self.query_one("#conversation", TextArea)
            current = conv.text
            conv.load_text(current + text)
        except Exception:
            pass

    def set_phase(self, phase: Phase) -> None:
        """Update current phase."""
        self.state.phase = phase
        save_state(self.state, self.config.get_state_path(self.project_root))
        try:
            status = self.query_one(StatusBar)
            status.update_phase(phase)
        except Exception:
            pass
