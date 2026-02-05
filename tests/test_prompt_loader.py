"""Tests for prompt loader."""
import tempfile
from pathlib import Path

from agent_collab.engine import load_prompt, substitute_variables, list_prompts


class TestSubstituteVariables:
    """Tests for variable substitution."""

    def test_simple_substitution(self):
        """Test basic variable substitution."""
        result = substitute_variables("Hello {{name}}!", name="World")
        assert result == "Hello World!"

    def test_multiple_variables(self):
        """Test multiple variables."""
        template = "{{greeting}} {{name}}, welcome to {{place}}!"
        result = substitute_variables(
            template, greeting="Hi", name="Alice", place="home"
        )
        assert result == "Hi Alice, welcome to home!"

    def test_unknown_variable_preserved(self):
        """Test that unknown variables are preserved."""
        result = substitute_variables("Hello {{name}} and {{unknown}}!", name="World")
        assert result == "Hello World and {{unknown}}!"

    def test_no_variables(self):
        """Test template with no variables."""
        result = substitute_variables("Hello World!")
        assert result == "Hello World!"


class TestLoadPrompt:
    """Tests for loading prompts from files."""

    def test_load_and_substitute(self):
        """Test loading prompt and substituting variables."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Review the plan at {{plan_path}}.")
            f.flush()
            result = load_prompt(Path(f.name), plan_path="/path/to/plan.md")

        assert result == "Review the plan at /path/to/plan.md."

    def test_load_nonexistent_raises(self):
        """Test loading nonexistent file raises error."""
        import pytest
        with pytest.raises(FileNotFoundError):
            load_prompt(Path("/nonexistent/template.md"))


class TestListPrompts:
    """Tests for listing prompt files."""

    def test_list_prompts(self):
        """Test listing prompt files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir)
            (prompts_dir / "01_first.md").write_text("First")
            (prompts_dir / "02_second.md").write_text("Second")
            (prompts_dir / "readme.txt").write_text("Not a prompt")

            prompts = list_prompts(prompts_dir)

            assert len(prompts) == 2
            assert prompts[0].name == "01_first.md"
            assert prompts[1].name == "02_second.md"

    def test_list_prompts_empty_dir(self):
        """Test listing prompts in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts = list_prompts(Path(tmpdir))
            assert prompts == []

    def test_list_prompts_nonexistent_dir(self):
        """Test listing prompts in nonexistent directory."""
        prompts = list_prompts(Path("/nonexistent/prompts"))
        assert prompts == []


class TestActualPrompts:
    """Tests for actual prompt templates in prompts/ directory."""

    def test_all_prompts_exist(self):
        """Test that all expected prompt files exist."""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        expected = [
            "01_refine_goal.md",
            "02_write_plan.md",
            "03_review_plan.md",
            "04_respond_comments.md",
            "05_execute_step.md",
            "06_recover_context.md",
        ]
        for name in expected:
            assert (prompts_dir / name).exists(), f"Missing prompt: {name}"

    def test_prompts_are_non_empty(self):
        """Test that all prompts have content."""
        prompts_dir = Path(__file__).parent.parent / "prompts"
        for prompt_file in list_prompts(prompts_dir):
            content = prompt_file.read_text()
            assert len(content) > 10, f"Prompt {prompt_file.name} is too short"
