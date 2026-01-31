"""Clone all 'tools' category repos to a local folder."""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import get_all_repos, GITHUB_OWNER, get_github_token, UTILS_REPOS_DIR

console = Console()


def clone_utils_repos(pull_existing: bool = False):
    """Clone all 'tools' category repos to the utils directory."""
    UTILS_REPOS_DIR.mkdir(parents=True, exist_ok=True)

    # Filter repos in the "tools" category
    all_repos = get_all_repos()
    repos = [r for r in all_repos if r.category == "tools"]
    token = get_github_token()

    console.print(f"[bold]Cloning {len(repos)} tools repos to {UTILS_REPOS_DIR}[/bold]\n")

    cloned = 0
    skipped = 0
    pulled = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for repo in repos:
            repo_dir = UTILS_REPOS_DIR / repo.name
            task = progress.add_task(f"{repo.name}", total=None)

            if repo_dir.exists():
                if pull_existing:
                    progress.update(task, description=f"[yellow]Pulling {repo.name}...[/yellow]")
                    result = subprocess.run(
                        ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        pulled += 1
                        progress.update(task, description=f"[blue]Pulled {repo.name}[/blue]")
                    else:
                        failed += 1
                        progress.update(task, description=f"[red]Failed to pull {repo.name}[/red]")
                else:
                    skipped += 1
                    progress.update(task, description=f"[dim]Skipped {repo.name} (exists)[/dim]")
            else:
                progress.update(task, description=f"[cyan]Cloning {repo.name}...[/cyan]")

                if token:
                    clone_url = f"https://{token}@github.com/{GITHUB_OWNER}/{repo.name}.git"
                else:
                    clone_url = f"https://github.com/{GITHUB_OWNER}/{repo.name}.git"

                result = subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, str(repo_dir)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    cloned += 1
                    progress.update(task, description=f"[green]Cloned {repo.name}[/green]")
                else:
                    failed += 1
                    progress.update(task, description=f"[red]Failed {repo.name}[/red]")
                    console.print(f"  [dim]{result.stderr.strip()}[/dim]")

            progress.remove_task(task)

    console.print()
    console.print(f"[green]Cloned: {cloned}[/green]")
    if pulled:
        console.print(f"[blue]Pulled: {pulled}[/blue]")
    console.print(f"[dim]Skipped: {skipped}[/dim]")
    if failed:
        console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"\n[bold]Repos at:[/bold] {UTILS_REPOS_DIR}")
