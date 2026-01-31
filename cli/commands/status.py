"""Check for uncommitted changes in utils repos."""

import subprocess
from rich.console import Console

from config import UTILS_REPOS_DIR

console = Console()


def check_status():
    """Check all repos in utils folder for uncommitted changes."""
    if not UTILS_REPOS_DIR.exists():
        console.print(f"[red]Utils directory not found: {UTILS_REPOS_DIR}[/red]")
        return

    repos_with_changes = []
    clean_repos = []

    for repo_dir in sorted(UTILS_REPOS_DIR.iterdir()):
        if not repo_dir.is_dir():
            continue
        git_dir = repo_dir / ".git"
        if not git_dir.exists():
            continue

        # Run git status --porcelain (empty output = clean)
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            repos_with_changes.append((repo_dir.name, result.stdout.strip()))
        else:
            clean_repos.append(repo_dir.name)

    # Display results
    if repos_with_changes:
        console.print(f"\n[bold red]Repos with uncommitted changes ({len(repos_with_changes)}):[/bold red]")
        for name, changes in repos_with_changes:
            console.print(f"\n[cyan]{name}[/cyan]")
            for line in changes.split("\n"):
                console.print(f"  {line}")
    else:
        console.print("\n[green]All repos are clean![/green]")

    console.print(f"\n[dim]Checked {len(repos_with_changes) + len(clean_repos)} repos in {UTILS_REPOS_DIR}[/dim]")
