"""TUI application for agent-collab."""
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane, TextArea, Static, Input
from textual.containers import Vertical

from ..config import Config, load_config
from ..engine import Phase, WorkflowController
from ..persistence import WorkflowState, load_state, save_state, state_exists


class ConversationPane(Vertical):
    """Pane for conversation with agents."""

    def compose(self) -> ComposeResult:
        yield TextArea(id="conversation", read_only=True)
        yield Input(placeholder="Type your message (or /plan to write plan)...", id="user-input")


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

    def __init__(self, phase: Phase, iteration: int = 0) -> None:
        super().__init__()
        self.phase = phase
        self.iteration = iteration

    def compose(self) -> ComposeResult:
        yield Static(self._format_status(), id="phase-display")

    def _format_status(self) -> str:
        return f"Phase: {self.phase.value} | Iteration: {self.iteration} | [Enter] Proceed [R] Refresh [Q] Quit"

    def update_status(self, phase: Phase, iteration: int) -> None:
        """Update displayed status."""
        self.phase = phase
        self.iteration = iteration
        display = self.query_one("#phase-display", Static)
        display.update(self._format_status())


class AgentCollabApp(App):
    """Main TUI application."""

    CSS = """
    ConversationPane {
        height: 100%;
    }

    #conversation {
        height: 1fr;
        min-height: 10;
    }

    #user-input {
        dock: bottom;
        height: 3;
        margin: 1 0;
    }

    #plan-content, #comments-content {
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
        Binding("q", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh", show=False),
    ]

    def __init__(
        self,
        project_root: Path,
        config: Config | None = None,
    ) -> None:
        super().__init__()
        self.project_root = project_root
        self.config = config or load_config()
        self._init_workflow()

    def _init_workflow(self) -> None:
        """Initialize workflow controller."""
        self.workflow = WorkflowController(
            self.project_root,
            self.config,
            on_output=self._on_agent_output,
            on_phase_change=self._on_phase_change,
        )

    def _on_agent_output(self, text: str) -> None:
        """Handle agent output."""
        self.call_from_thread(self.update_conversation, text)

    def _on_phase_change(self, phase: Phase) -> None:
        """Handle phase change."""
        self.call_from_thread(self._update_status_bar)
        self.call_from_thread(self.action_refresh)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Conversation", id="tab-conversation"):
                yield ConversationPane()
            with TabPane("Plan", id="tab-plan"):
                yield PlanTab(self.config.get_plan_path(self.project_root))
            with TabPane("Comments", id="tab-comments"):
                yield CommentsTab(self.config.get_comments_path(self.project_root))
        yield StatusBar(self.workflow.state.phase, self.workflow.state.iteration)
        yield Footer()

    async def on_mount(self) -> None:
        """Handle app mount - check for existing session."""
        state_path = self.config.get_state_path(self.project_root)
        if state_exists(state_path) and self.workflow.state.phase != Phase.DONE:
            self.update_conversation(
                f"[Recovered session - Phase: {self.workflow.state.phase.value}, "
                f"Iteration: {self.workflow.state.iteration}]\n\n"
            )

        # Show welcome message
        self.update_conversation(
            "Welcome to Agent Collab!\n"
            "Describe your goal, then type /plan when ready to create a plan.\n\n"
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()
        if not user_input:
            return

        # Clear input
        event.input.value = ""

        # Add user message to conversation
        self.update_conversation(f"You: {user_input}\n\n")

        # Handle commands
        if user_input.lower() == "/plan":
            await self._handle_plan_command()
        elif user_input.lower() == "/approve":
            await self._handle_approve_command()
        elif user_input.lower() == "/execute":
            await self._handle_execute_command()
        else:
            await self._handle_user_message(user_input)

    async def _handle_user_message(self, message: str) -> None:
        """Handle regular user message."""
        phase = self.workflow.state.phase

        if phase in (Phase.INIT, Phase.REFINE_GOAL):
            self.update_conversation("Agent (Planner): ")
            await self.workflow.start_refinement(message)
            self.update_conversation("\n\n")
        else:
            self.update_conversation(f"[Current phase: {phase.value} - use appropriate command]\n\n")

    async def _handle_plan_command(self) -> None:
        """Handle /plan command."""
        self.update_conversation("[Writing plan...]\n\nAgent (Planner): ")
        await self.workflow.write_plan()
        self.update_conversation("\n\n[Plan written. Starting review...]\n\nAgent (Reviewer): ")
        await self.workflow.review_plan()
        self.update_conversation("\n\n")
        self.action_refresh()

        if self.workflow.is_approved():
            self.update_conversation("[Plan APPROVED! Type /execute to begin execution.]\n\n")
        else:
            self.update_conversation(
                f"[Review complete - Iteration {self.workflow.state.iteration}. "
                "Press Enter to continue iteration or type /approve to force approve.]\n\n"
            )

    async def _handle_approve_command(self) -> None:
        """Handle /approve command (force approve)."""
        if self.workflow.state.phase in (Phase.REVIEW, Phase.RESPOND):
            # Force transition to approved
            self.workflow.state.phase = Phase.APPROVED
            self.workflow._save_state()
            self._update_status_bar()
            self.update_conversation("[Plan force-approved. Type /execute to begin.]\n\n")
        else:
            self.update_conversation(f"[Cannot approve in phase: {self.workflow.state.phase.value}]\n\n")

    async def _handle_execute_command(self) -> None:
        """Handle /execute command."""
        if self.workflow.state.phase != Phase.APPROVED:
            self.update_conversation(f"[Cannot execute - plan not approved (phase: {self.workflow.state.phase.value})]\n\n")
            return

        self.update_conversation("[Execution phase - implement steps one by one]\n")
        self.update_conversation("[Note: In MVP, agent will read plan and execute. Press Enter after each step.]\n\n")

        # For MVP, just transition to execute phase
        self.workflow.state.phase = Phase.EXECUTE
        self.workflow._save_state()
        self._update_status_bar()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

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

    def update_conversation(self, text: str) -> None:
        """Add text to conversation area."""
        try:
            conv = self.query_one("#conversation", TextArea)
            current = conv.text
            conv.load_text(current + text)
            # Scroll to bottom
            conv.scroll_end()
        except Exception:
            pass

    def _update_status_bar(self) -> None:
        """Update status bar with current state."""
        try:
            status = self.query_one(StatusBar)
            status.update_status(self.workflow.state.phase, self.workflow.state.iteration)
        except Exception:
            pass
