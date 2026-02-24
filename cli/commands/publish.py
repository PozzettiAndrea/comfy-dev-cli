"""Publish test results to gh-pages branch.

This module implements the `cds publish` command which merges local test results
(typically linux-gpu) into the gh-pages branch, preserving CI-published results
for other platforms (e.g., windows-cpu from GitHub Actions).

gh-pages structure:
  {branch}/
    index.html            <- platform tabs
    {platform}/
      index.html          <- test report
      results.json
  index.html              <- branch switcher
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

from commands.show import find_latest_log, find_branches, PLATFORM_IDS
from commands.test import find_repo

console = Console()

# Try to import report utilities from comfy-test
try:
    sys.path.insert(0, str(Path.home() / "utils" / "comfy-test" / "src"))
    from comfy_test.reporting.html_report import (
        generate_html_report,
        generate_root_index,
        generate_branch_root_index,
    )
    HAS_REPORT_UTILS = True
except ImportError:
    HAS_REPORT_UTILS = False


def publish_results(repo_name: str, force: bool = False, push: bool = True) -> int:
    """Publish local test results to gh-pages branch.

    Finds the latest test results, merges platform results into the existing
    gh-pages structure (preserving CI-published platforms), regenerates HTML
    indexes, and pushes.

    Args:
        repo_name: Repository name (e.g., depthanythingv3, geometrypack)
        force: Skip uncommitted changes check
        push: Push to remote (default: True)

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
        console.print(f"[dim]Run 'cds dev test {repo_name}' first[/dim]")
        return 1

    console.print(f"[dim]Results: {log_folder}[/dim]")

    # 4. Discover branches in the log folder
    branches = find_branches(log_folder)
    if not branches:
        console.print(f"[red]No branch/platform structure found in {log_folder}[/red]")
        console.print(f"[dim]Expected: {log_folder}/{{branch}}/{{platform}}/results.json[/dim]")
        return 1

    for b in branches:
        # Show which platforms have results in this branch
        platforms_found = [
            pid for pid in PLATFORM_IDS
            if (b / pid / "results.json").exists()
        ]
        console.print(f"[dim]  Branch: {b.name} -> {', '.join(platforms_found)}[/dim]")

    # 5. Publish using worktree
    return _publish_with_worktree(repo_path, branches, push)


def _publish_with_worktree(
    repo_path: Path,
    branches: list[Path],
    push: bool = True,
) -> int:
    """Publish using git worktree to avoid touching the main branch.

    Merges local results per-platform into gh-pages, preserving existing
    results from CI for platforms we don't have new results for.

    Args:
        repo_path: Path to the git repository
        branches: List of branch folders containing platform subdirs
        push: If True, push to remote after committing

    Returns:
        Exit code (0 for success, 1 for error)
    """
    repo_name = repo_path.name

    # Fetch gh-pages from remote (may only exist on origin, not locally)
    console.print("[dim]Fetching gh-pages from origin...[/dim]")
    # Delete stale local gh-pages branch if it exists (avoids ref conflicts)
    subprocess.run(
        ["git", "branch", "-D", "gh-pages"],
        cwd=repo_path,
        capture_output=True,
    )
    fetch_result = subprocess.run(
        ["git", "fetch", "origin", "gh-pages"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    remote_has_gh_pages = fetch_result.returncode == 0

    # Create temp directory for worktree
    with tempfile.TemporaryDirectory() as tmpdir:
        worktree_path = Path(tmpdir) / "gh-pages"

        try:
            if remote_has_gh_pages:
                # Checkout gh-pages from the fetched remote ref
                console.print("[dim]Checking out gh-pages branch...[/dim]")

                # Create local branch from fetched remote
                result = subprocess.run(
                    ["git", "worktree", "add", "-b", "gh-pages", str(worktree_path), "FETCH_HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    console.print(f"[red]Failed to checkout gh-pages: {result.stderr}[/red]")
                    return 1
            else:
                # Create new orphan gh-pages branch
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

            # --- Merge local results into gh-pages (per-branch, per-platform) ---
            for branch_folder in branches:
                branch_name = branch_folder.name
                gh_branch_dir = worktree_path / branch_name
                gh_branch_dir.mkdir(parents=True, exist_ok=True)

                for platform_id in PLATFORM_IDS:
                    src_platform = branch_folder / platform_id
                    if not (src_platform / "results.json").exists():
                        continue

                    console.print(f"[dim]  Copying {branch_name}/{platform_id}...[/dim]")
                    dst_platform = gh_branch_dir / platform_id

                    # Remove old version of THIS platform only, preserve others
                    if dst_platform.exists():
                        shutil.rmtree(dst_platform)
                    shutil.copytree(src_platform, dst_platform)

                # Regenerate HTML reports for all platforms in this branch
                if HAS_REPORT_UTILS:
                    for platform_id in PLATFORM_IDS:
                        platform_dir = gh_branch_dir / platform_id
                        if (platform_dir / "results.json").exists():
                            try:
                                generate_html_report(platform_dir, repo_name, current_platform=platform_id)
                            except Exception as e:
                                console.print(f"[yellow]  Warning generating {platform_id} report: {e}[/yellow]")

                    # Regenerate branch index (platform tabs)
                    console.print(f"[dim]  Generating {branch_name} index...[/dim]")
                    generate_root_index(gh_branch_dir, repo_name)

            # Regenerate root index (branch switcher)
            if HAS_REPORT_UTILS:
                console.print("[dim]Generating root index (branch switcher)...[/dim]")
                generate_branch_root_index(worktree_path, repo_name)

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
                    parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
                else:
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
