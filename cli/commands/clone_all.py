"""Clone all ComfyUI nodes to a local folder via symlinks into setup environments."""

import os
import shutil
import subprocess
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from commands.get import setup_comfyui
from config import get_all_repos, get_repos_by_category, ALL_REPOS_DIR, INSTALL_DIR, get_repo_config_map

console = Console()


def clone_all_repos(pull_existing: bool = False, threshold: int = 0):
    """Symlink all ComfyUI node repos into all_repos from setup environments."""
    ALL_REPOS_DIR.mkdir(parents=True, exist_ok=True)

    repos = [r for r in get_all_repos() if r.category == "comfyui"]
    if threshold > 0:
        repos = [r for r in repos if r.stars >= threshold]

    config_map = get_repo_config_map()

    label = f"Symlinking {len(repos)} ComfyUI node repos"
    if threshold > 0:
        label += f" (>= {threshold} stars)"
    console.print(f"[bold]{label} to {ALL_REPOS_DIR}[/bold]\n")

    setup_count = 0
    symlinked = 0
    replaced = 0
    skipped_no_config = 0
    skipped = 0
    pulled = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for repo in repos:
            link_path = ALL_REPOS_DIR / repo.name
            task = progress.add_task(f"{repo.name}", total=None)

            # 1. Check config mapping
            if repo.name not in config_map:
                skipped_no_config += 1
                progress.update(task, description=f"[dim]Skipped {repo.name} (no setup config)[/dim]")
                progress.remove_task(task)
                continue

            config_name, folder_name = config_map[repo.name]
            env_dir = INSTALL_DIR / folder_name
            target_path = env_dir / "ComfyUI" / "custom_nodes" / repo.name

            # 2. Ensure setup environment exists
            if not env_dir.exists():
                progress.update(task, description=f"[cyan]Setting up {folder_name} environment...[/cyan]")
                saved_cwd = os.getcwd()
                try:
                    setup_comfyui(config_name)
                    setup_count += 1
                except Exception as e:
                    failed += 1
                    progress.update(task, description=f"[red]Failed setup for {repo.name}: {e}[/red]")
                    progress.remove_task(task)
                    continue
                finally:
                    os.chdir(saved_cwd)

            # 3. Verify target path exists
            if not target_path.exists():
                failed += 1
                progress.update(task, description=f"[red]{repo.name}: target not found at {target_path}[/red]")
                progress.remove_task(task)
                continue

            # 4. Handle existing entries in all_repos/
            if link_path.is_symlink():
                current_target = link_path.resolve()
                if current_target == target_path.resolve():
                    # Correct symlink already exists
                    if pull_existing:
                        progress.update(task, description=f"[yellow]Pulling {repo.name}...[/yellow]")
                        result = subprocess.run(
                            ["git", "-C", str(target_path), "pull", "--ff-only"],
                            capture_output=True, text=True,
                        )
                        if result.returncode == 0:
                            pulled += 1
                            progress.update(task, description=f"[blue]Pulled {repo.name}[/blue]")
                        else:
                            failed += 1
                            progress.update(task, description=f"[red]Failed to pull {repo.name}[/red]")
                    else:
                        skipped += 1
                        progress.update(task, description=f"[dim]Skipped {repo.name} (symlink exists)[/dim]")
                    progress.remove_task(task)
                    continue
                else:
                    # Wrong/broken symlink - remove and recreate
                    link_path.unlink()

            elif link_path.exists():
                # Real directory (old behavior) - check for uncommitted changes
                progress.update(task, description=f"[yellow]Checking {repo.name} for uncommitted changes...[/yellow]")
                result = subprocess.run(
                    ["git", "-C", str(link_path), "status", "--porcelain"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    failed += 1
                    progress.update(task, description=f"[red]Skipped {repo.name} (has uncommitted changes in old clone)[/red]")
                    progress.remove_task(task)
                    continue
                # Safe to remove
                shutil.rmtree(link_path)
                replaced += 1

            # 5. Create symlink
            progress.update(task, description=f"[cyan]Symlinking {repo.name}...[/cyan]")
            try:
                link_path.symlink_to(target_path)
                symlinked += 1
                progress.update(task, description=f"[green]Symlinked {repo.name}[/green]")
            except OSError as e:
                failed += 1
                progress.update(task, description=f"[red]Failed to symlink {repo.name}: {e}[/red]")

            progress.remove_task(task)

    console.print()
    if setup_count:
        console.print(f"[cyan]Environments set up: {setup_count}[/cyan]")
    console.print(f"[green]Symlinked: {symlinked}[/green]")
    if replaced:
        console.print(f"[yellow]Replaced (old clone -> symlink): {replaced}[/yellow]")
    if pulled:
        console.print(f"[blue]Pulled: {pulled}[/blue]")
    console.print(f"[dim]Skipped (exists): {skipped}[/dim]")
    if skipped_no_config:
        console.print(f"[dim]Skipped (no setup config): {skipped_no_config}[/dim]")
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
