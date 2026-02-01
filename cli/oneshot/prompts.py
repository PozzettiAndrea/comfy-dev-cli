"""Prompts for oneshot CLI commands."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name):
    """Load a prompt from a markdown file."""
    prompt_path = _PROMPTS_DIR / f"{name}-prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text()


# Lazy-loaded prompts
def get_initial_assessment_prompt():
    return load_prompt("initial-assessment")


def get_discussion_prompt():
    return load_prompt("discussion")


def get_considerations_prompt():
    return load_prompt("considerations")


def get_fill_prompt():
    return load_prompt("fill")


def get_workflows_prompt():
    return load_prompt("workflows")
