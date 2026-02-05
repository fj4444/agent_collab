"""Prompt template loading and variable substitution."""
import re
from pathlib import Path


def load_prompt(template_path: Path, **variables: str) -> str:
    """Load prompt template and substitute variables.

    Variables in template use {{variable_name}} syntax.

    Args:
        template_path: Path to the .md template file.
        **variables: Variable name-value pairs for substitution.

    Returns:
        Prompt string with variables substituted.

    Raises:
        FileNotFoundError: If template file doesn't exist.
    """
    content = template_path.read_text()
    return substitute_variables(content, **variables)


def substitute_variables(template: str, **variables: str) -> str:
    """Substitute {{variable}} placeholders in template.

    Args:
        template: Template string with {{variable}} placeholders.
        **variables: Variable name-value pairs.

    Returns:
        String with variables substituted.
    """
    def replace(match: re.Match) -> str:
        var_name = match.group(1).strip()
        return variables.get(var_name, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", replace, template)


def list_prompts(prompts_dir: Path) -> list[Path]:
    """List all prompt template files in directory.

    Args:
        prompts_dir: Directory containing prompt templates.

    Returns:
        Sorted list of .md files in the directory.
    """
    if not prompts_dir.exists():
        return []
    return sorted(prompts_dir.glob("*.md"))
