"""Clone CUDA geometry repos to a local folder."""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import INSTALL_DIR, get_github_token

console = Console()

CUDAGEOM_REPOS_DIR = INSTALL_DIR / "cudageom"

CUDAGEOM_REPOS = [
    ("PozzettiAndrea", "quadwild-bimdf-cuda"),
    ("PozzettiAndrea", "QuadriFlow-cuda"),
    ("PozzettiAndrea", "instant-meshes-cuda"),
    ("PozzettiAndrea", "mmg-cuda"),
    ("PozzettiAndrea", "geogram-cuda"),
    ("PozzettiAndrea", "pmp-library-cuda"),
]


def clone_cudageom_repos(pull_existing: bool = False):
    """Clone all CUDA geometry repos to the cudageom directory."""
    CUDAGEOM_REPOS_DIR.mkdir(parents=True, exist_ok=True)

    token = get_github_token()

    console.print(f"[bold]Cloning {len(CUDAGEOM_REPOS)} cudageom repos to {CUDAGEOM_REPOS_DIR}[/bold]\n")

    cloned = 0
    skipped = 0
    pulled = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for owner, name in CUDAGEOM_REPOS:
            repo_dir = CUDAGEOM_REPOS_DIR / name
            task = progress.add_task(f"{name}", total=None)

            if repo_dir.exists():
                if pull_existing:
                    progress.update(task, description=f"[yellow]Pulling {name}...[/yellow]")
                    result = subprocess.run(
                        ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        pulled += 1
                        progress.update(task, description=f"[blue]Pulled {name}[/blue]")
                    else:
                        failed += 1
                        progress.update(task, description=f"[red]Failed to pull {name}[/red]")
                else:
                    skipped += 1
                    progress.update(task, description=f"[dim]Skipped {name} (exists)[/dim]")
            else:
                progress.update(task, description=f"[cyan]Cloning {name}...[/cyan]")

                if token:
                    clone_url = f"https://{token}@github.com/{owner}/{name}.git"
                else:
                    clone_url = f"https://github.com/{owner}/{name}.git"

                result = subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, str(repo_dir)],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    cloned += 1
                    progress.update(task, description=f"[green]Cloned {name}[/green]")
                else:
                    failed += 1
                    progress.update(task, description=f"[red]Failed {name}[/red]")
                    console.print(f"  [dim]{result.stderr.strip()}[/dim]")

            progress.remove_task(task)

    console.print()
    console.print(f"[green]Cloned: {cloned}[/green]")
    if pulled:
        console.print(f"[blue]Pulled: {pulled}[/blue]")
    console.print(f"[dim]Skipped: {skipped}[/dim]")
    if failed:
        console.print(f"[red]Failed: {failed}[/red]")
    console.print(f"\n[bold]Repos at:[/bold] {CUDAGEOM_REPOS_DIR}")
