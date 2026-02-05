"""Workflow controller - coordinates the entire collaboration flow."""
import asyncio
from pathlib import Path
from typing import Callable, AsyncIterator

from ..config import Config
from ..engine import Phase, can_transition, load_prompt
from ..persistence import WorkflowState, save_state, load_state
from ..adapters import AgentAdapter, create_adapter


class WorkflowController:
    """Controls the agent collaboration workflow."""

    def __init__(
        self,
        project_root: Path,
        config: Config,
        on_output: Callable[[str], None] | None = None,
        on_phase_change: Callable[[Phase], None] | None = None,
    ) -> None:
        """Initialize workflow controller.

        Args:
            project_root: Root directory of the project.
            config: Configuration object.
            on_output: Callback for agent output.
            on_phase_change: Callback when phase changes.
        """
        self.project_root = project_root
        self.config = config
        self.on_output = on_output or (lambda x: None)
        self.on_phase_change = on_phase_change or (lambda x: None)

        # Load or create state
        self.state = self._load_or_init_state()

        # Create adapters
        self.planner = create_adapter(config.roles.planner, str(project_root))
        self.reviewer = create_adapter(config.roles.reviewer, str(project_root))

        # Prompts directory
        self.prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"

    def _load_or_init_state(self) -> WorkflowState:
        """Load existing state or create new one."""
        state_path = self.config.get_state_path(self.project_root)
        state = load_state(state_path)
        if state is None:
            state = WorkflowState(phase=Phase.INIT)
            self._ensure_workdir()
        return state

    def _ensure_workdir(self) -> None:
        """Ensure workflow directory exists."""
        workdir = self.config.get_workdir(self.project_root)
        workdir.mkdir(parents=True, exist_ok=True)

    def _save_state(self) -> None:
        """Save current state to disk."""
        save_state(self.state, self.config.get_state_path(self.project_root))

    def _set_phase(self, phase: Phase) -> None:
        """Transition to a new phase."""
        if not can_transition(self.state.phase, phase):
            raise ValueError(f"Invalid transition: {self.state.phase} -> {phase}")
        self.state.phase = phase
        self._save_state()
        self.on_phase_change(phase)

    async def _stream_agent(self, adapter: AgentAdapter, prompt: str) -> str:
        """Send prompt to agent and stream output.

        Returns:
            Complete response text.
        """
        full_response = []
        async for chunk in adapter.send(prompt):
            self.on_output(chunk)
            full_response.append(chunk)
        return "".join(full_response)

    def get_plan_content(self) -> str:
        """Get current plan content."""
        plan_path = self.config.get_plan_path(self.project_root)
        if plan_path.exists():
            return plan_path.read_text()
        return ""

    def get_comments_content(self) -> str:
        """Get current comments content."""
        comments_path = self.config.get_comments_path(self.project_root)
        if comments_path.exists():
            return comments_path.read_text()
        return ""

    def is_approved(self) -> bool:
        """Check if plan is approved based on comments."""
        content = self.get_comments_content()
        return content.strip().startswith("[APPROVED]")

    def is_max_iterations(self) -> bool:
        """Check if max iterations reached."""
        return self.state.iteration >= self.config.workflow.max_iterations

    async def start_refinement(self, user_input: str) -> None:
        """Start or continue goal refinement phase.

        Args:
            user_input: User's input/goal description.
        """
        if self.state.phase == Phase.INIT:
            self._set_phase(Phase.REFINE_GOAL)

        # Load refine goal prompt
        prompt_path = self.prompts_dir / "01_refine_goal.md"
        base_prompt = load_prompt(prompt_path)
        full_prompt = f"{base_prompt}\n\nUser: {user_input}"

        await self._stream_agent(self.planner, full_prompt)

    async def write_plan(self) -> None:
        """Transition to write plan phase."""
        self._set_phase(Phase.WRITE_PLAN)

        prompt_path = self.prompts_dir / "02_write_plan.md"
        prompt = load_prompt(
            prompt_path,
            plan_path=str(self.config.get_plan_path(self.project_root)),
        )

        await self._stream_agent(self.planner, prompt)
        self._set_phase(Phase.REVIEW)

    async def review_plan(self) -> None:
        """Have reviewer review the plan."""
        prompt_path = self.prompts_dir / "03_review_plan.md"
        prompt = load_prompt(
            prompt_path,
            plan_path=str(self.config.get_plan_path(self.project_root)),
            comments_path=str(self.config.get_comments_path(self.project_root)),
        )

        await self._stream_agent(self.reviewer, prompt)
        self.state.iteration += 1
        self._save_state()

        if self.is_approved():
            self._set_phase(Phase.APPROVED)
        else:
            self._set_phase(Phase.RESPOND)

    async def respond_to_comments(self) -> None:
        """Have planner respond to review comments."""
        prompt_path = self.prompts_dir / "04_respond_comments.md"
        prompt = load_prompt(
            prompt_path,
            plan_path=str(self.config.get_plan_path(self.project_root)),
            comments_path=str(self.config.get_comments_path(self.project_root)),
        )

        await self._stream_agent(self.planner, prompt)
        self._set_phase(Phase.REVIEW)

    async def execute_step(self, step_number: int, step_content: str) -> None:
        """Execute a single step from the plan.

        Args:
            step_number: Step number (1-indexed).
            step_content: Content/description of the step.
        """
        if self.state.phase == Phase.APPROVED:
            self._set_phase(Phase.EXECUTE)

        prompt_path = self.prompts_dir / "05_execute_step.md"
        prompt = load_prompt(
            prompt_path,
            step_number=str(step_number),
            step_content=step_content,
            plan_path=str(self.config.get_plan_path(self.project_root)),
        )

        await self._stream_agent(self.planner, prompt)

    def mark_done(self) -> None:
        """Mark workflow as done."""
        self._set_phase(Phase.DONE)

    async def recover_context(self) -> None:
        """Recover context for resumed session."""
        prompt_path = self.prompts_dir / "06_recover_context.md"
        prompt = load_prompt(
            prompt_path,
            plan_path=str(self.config.get_plan_path(self.project_root)),
            plan_content=self.get_plan_content() or "(empty)",
            comments_path=str(self.config.get_comments_path(self.project_root)),
            comments_content=self.get_comments_content() or "(empty)",
            phase=self.state.phase.value,
            iteration=str(self.state.iteration),
        )

        # Send to whichever agent is active based on phase
        if self.state.phase in (Phase.REVIEW,):
            await self._stream_agent(self.reviewer, prompt)
        else:
            await self._stream_agent(self.planner, prompt)
