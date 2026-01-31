"""Publish test results to gh-pages branch.

This module implements the `ct publish` command which publishes test results
to a gh-pages branch for GitHub Pages hosting.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

from commands.show import find_latest_log
from commands.test import find_repo

console = Console()

# Try to import report utilities
try:
    sys.path.insert(0, str(Path.home() / "utils" / "comfy-test" / "src"))
    from comfy_test.report import has_platform_subdirs, PLATFORMS
    HAS_REPORT_UTILS = True
except ImportError:
    HAS_REPORT_UTILS = False
    PLATFORMS = [
        {'id': 'linux-cpu'}, {'id': 'linux-gpu'},
        {'id': 'windows-cpu'}, {'id': 'windows-gpu'},
        {'id': 'windows-portable-cpu'}, {'id': 'windows-portable-gpu'},
    ]

    def has_platform_subdirs(output_dir):
        for p in PLATFORMS:
            if (output_dir / p['id'] / 'index.html').exists():
                return True
        return False


def publish_results(repo_name: str, force: bool = False, push: bool = False) -> int:
    """Publish test results to gh-pages branch.

    Args:
        repo_name: Repository name (e.g., depthanythingv3, geometrypack)
        force: Skip uncommitted changes check
        push: Actually push to remote (default: just prepare locally)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # 1. Find repo
    repo_path = find_repo(repo_name)
    if not repo_path:
        return 1

    console.print(f"[dim]Repo: {repo_path}[/dim]")

    # 2. Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip() and not force:
        console.print("[red]Uncommitted changes detected![/red]")
        console.print(result.stdout)
        console.print("[dim]Commit changes first, or use --force to skip this check[/dim]")
        return 1

    # 3. Find latest test results
    log_folder = find_latest_log(repo_name)
    if not log_folder:
        console.print(f"[red]No test results found for '{repo_name}'[/red]")
        console.print(f"[dim]Run 'ct test {repo_name}' first[/dim]")
        return 1

    console.print(f"[dim]Results: {log_folder}[/dim]")

    # Check required files exist
    index_html = log_folder / "index.html"
    if not index_html.exists():
        console.print(f"[red]No index.html in {log_folder}[/red]")
        return 1

    # 4. Create/update gh-pages branch using git worktree
    return _publish_with_worktree(repo_path, log_folder, push)


def _publish_with_worktree(repo_path: Path, log_folder: Path, push: bool = False) -> int:
    """Publish using git worktree to avoid touching the main branch.

    Args:
        repo_path: Path to the git repository
        log_folder: Path to the test results folder
        push: If True, push to remote after committing

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Check if gh-pages branch exists (locally or remotely)
    result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    branches = result.stdout
    gh_pages_exists = "gh-pages" in branches

    # Create temp directory for worktree
    with tempfile.TemporaryDirectory() as tmpdir:
        worktree_path = Path(tmpdir) / "gh-pages"

        try:
            if gh_pages_exists:
                # Checkout existing gh-pages branch
                console.print("[dim]Checking out existing gh-pages branch...[/dim]")
                result = subprocess.run(
                    ["git", "worktree", "add", str(worktree_path), "gh-pages"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    # Branch might exist remotely but not locally
                    result = subprocess.run(
                        ["git", "worktree", "add", "-b", "gh-pages", str(worktree_path), "origin/gh-pages"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        console.print(f"[red]Failed to checkout gh-pages: {result.stderr}[/red]")
                        return 1
            else:
                # Create new orphan gh-pages branch (worktree --orphan not available in older git)
                console.print("[dim]Creating new gh-pages branch...[/dim]")

                # Create worktree with detached HEAD first
                result = subprocess.run(
                    ["git", "worktree", "add", "--detach", str(worktree_path)],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to create worktree: {result.stderr}[/red]")
                    return 1

                # Now create orphan branch inside the worktree
                result = subprocess.run(
                    ["git", "checkout", "--orphan", "gh-pages"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to create orphan branch: {result.stderr}[/red]")
                    return 1

                # Remove all files from index (orphan branch starts with staged files)
                subprocess.run(
                    ["git", "rm", "-rf", "--cached", "."],
                    cwd=worktree_path,
                    capture_output=True,
                )

            # Check if multi-platform structure
            is_multi_platform = has_platform_subdirs(log_folder)

            if is_multi_platform:
                # Multi-platform: preserve existing platform results, only update what we have
                console.print("[dim]Detected multi-platform structure[/dim]")

                # Copy root index.html (regenerate it)
                root_index = log_folder / "index.html"
                if root_index.exists():
                    shutil.copy2(root_index, worktree_path / "index.html")

                # Copy each platform subdir we have results for
                for p in PLATFORMS:
                    platform_id = p['id']
                    src_platform_dir = log_folder / platform_id
                    dst_platform_dir = worktree_path / platform_id

                    if (src_platform_dir / "index.html").exists():
                        console.print(f"[dim]Copying {platform_id}...[/dim]")
                        # Remove existing platform dir if present
                        if dst_platform_dir.exists():
                            shutil.rmtree(dst_platform_dir)
                        # Copy the platform results
                        shutil.copytree(src_platform_dir, dst_platform_dir)
            else:
                # Legacy single-platform: clear and replace everything
                for item in worktree_path.iterdir():
                    if item.name == ".git":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

                # Copy test results to worktree
                console.print("[dim]Copying test results...[/dim]")
                files_to_copy = ["index.html", "results.json"]
                dirs_to_copy = ["screenshots", "videos"]

                for filename in files_to_copy:
                    src = log_folder / filename
                    if src.exists():
                        shutil.copy2(src, worktree_path / filename)

                for dirname in dirs_to_copy:
                    src = log_folder / dirname
                    if src.exists():
                        shutil.copytree(src, worktree_path / dirname)

            # Add .nojekyll file to disable Jekyll processing
            (worktree_path / ".nojekyll").touch()

            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=worktree_path,
                check=True,
            )

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )
            if not result.stdout.strip():
                console.print("[yellow]No changes to publish[/yellow]")
                return 0

            # Commit
            console.print("[dim]Committing...[/dim]")
            subprocess.run(
                ["git", "commit", "-m", "Update test results"],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )

            # Get repo URL for GitHub Pages URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            remote_url = result.stdout.strip()
            pages_url = None

            if "github.com" in remote_url:
                # Handle both SSH and HTTPS URLs
                if remote_url.startswith("git@"):
                    # git@github.com:user/repo.git
                    parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
                else:
                    # https://github.com/user/repo.git
                    parts = remote_url.replace("https://github.com/", "").replace(".git", "").split("/")

                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    pages_url = f"https://{owner}.github.io/{repo}/"

            if push:
                # Push to remote
                console.print("[dim]Pushing to origin/gh-pages...[/dim]")
                result = subprocess.run(
                    ["git", "push", "-u", "origin", "gh-pages"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to push: {result.stderr}[/red]")
                    return 1

                console.print(f"\n[green bold]Published![/green bold]")
                if pages_url:
                    console.print(f"[cyan]{pages_url}[/cyan]")
                    console.print(f"[dim]Note: May take a minute for GitHub Pages to update[/dim]")
            else:
                # Local only - show what would happen
                console.print(f"\n[green]Committed to local gh-pages branch[/green]")
                console.print(f"[dim]Run with --push to push to remote[/dim]")
                if pages_url:
                    console.print(f"[dim]URL will be: {pages_url}[/dim]")

            return 0

        finally:
            # Clean up worktree
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=repo_path,
                capture_output=True,
            )
