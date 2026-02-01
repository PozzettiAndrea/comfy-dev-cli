"""Clone all ComfyUI nodes to a local folder."""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import get_all_repos, GITHUB_OWNER, get_github_token, ALL_REPOS_DIR

console = Console()


def clone_all_repos(pull_existing: bool = False, threshold: int = 0):
    """Clone all ComfyUI node repos to the all_repos directory."""
    ALL_REPOS_DIR.mkdir(parents=True, exist_ok=True)

    repos = [r for r in get_all_repos() if r.category == "comfyui"]
    if threshold > 0:
        repos = [r for r in repos if r.stars >= threshold]
    token = get_github_token()

    label = f"Cloning {len(repos)} ComfyUI node repos"
    if threshold > 0:
        label += f" (>= {threshold} stars)"
    console.print(f"[bold]{label} to {ALL_REPOS_DIR}[/bold]\n")

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
            repo_dir = ALL_REPOS_DIR / repo.name
            task = progress.add_task(f"{repo.name}", total=None)

            if repo_dir.exists():
                if pull_existing:
                    # Pull latest changes
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
                # Clone the repo
                progress.update(task, description=f"[cyan]Cloning {repo.name}...[/cyan]")

                # Use token in URL for authentication
                if token:
                    clone_url = f"https://{token}@github.com/{GITHUB_OWNER}/{repo.name}.git"
                else:
                    clone_url = f"https://github.com/{GITHUB_OWNER}/{repo.name}.git"

                result = subprocess.run(
                    ["git", "clone", "--depth", "1", "-b", "dev", clone_url, str(repo_dir)],
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
    console.print(f"\n[bold]Repos at:[/bold] {ALL_REPOS_DIR}")


def pull_all_repos():
    """Pull latest changes for all existing ComfyUI node repos."""
    repos = get_repos_by_category("comfyui")

    console.print(f"[bold]Pulling ComfyUI node repos in {ALL_REPOS_DIR}[/bold]\n")

    pulled = 0
    skipped = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for repo in repos:
            repo_dir = ALL_REPOS_DIR / repo.name
            task = progress.add_task(f"{repo.name}", total=None)

            if repo_dir.exists():
                progress.update(task, description=f"[yellow]Pulling {repo.name}...[/yellow]")
                result = subprocess.run(
                    ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    pulled += 1
                    progress.update(task, description=f"[green]Pulled {repo.name}[/green]")
                else:
                    failed += 1
                    progress.update(task, description=f"[red]Failed to pull {repo.name}[/red]")
                    console.print(f"  [dim]{result.stderr.strip()}[/dim]")
            else:
                skipped += 1
                progress.update(task, description=f"[dim]Skipped {repo.name} (not cloned)[/dim]")

            progress.remove_task(task)

    console.print()
    console.print(f"[green]Pulled: {pulled}[/green]")
    if skipped:
        console.print(f"[dim]Skipped (not cloned): {skipped}[/dim]")
    if failed:
        console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"\n[bold]Repos at:[/bold] {ALL_REPOS_DIR}")
