"""Show test results status from gh-pages across all repos.

Fetches results.json from each repo's gh-pages branch to show
which platforms are passing/failing and whether results match
the current commit.
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.table import Table

from config import GITHUB_OWNER

console = Console()

# Repos dir
ALL_REPOS_DIR = Path.home() / "all_repos"

# Branches to check on gh-pages
BRANCHES = ["dev", "main"]


def _get_repo_slugs() -> list[tuple[str, str, Path]]:
    """Get (name, owner/repo slug, local path) for each repo in all_repos/."""
    repos = []
    if not ALL_REPOS_DIR.exists():
        return repos

    for entry in sorted(ALL_REPOS_DIR.iterdir()):
        if not entry.is_symlink() and not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue

        real_path = entry.resolve()
        if not real_path.exists():
            continue

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=real_path, capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                continue
            url = result.stdout.strip()
            # Extract owner/repo from SSH or HTTPS URL
            if "github.com" in url:
                if url.startswith("git@"):
                    slug = url.replace("git@github.com:", "").replace(".git", "")
                else:
                    slug = url.replace("https://github.com/", "").replace(".git", "")
                repos.append((entry.name, slug, real_path))
        except Exception:
            continue

    return repos


def _get_local_head(repo_path: Path) -> str:
    """Get the current HEAD commit hash of a local repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _get_local_branch(repo_path: Path) -> str:
    """Get the current branch name of a local repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _fetch_gh_pages_status(slug: str) -> dict:
    """Fetch results.json from each branch/platform on gh-pages.

    Returns:
        {
            "dev": {
                "linux-gpu": {"success": True, "commit_hash": "abc123", "timestamp": "..."},
                "windows-cpu": {...},
            },
            "main": {...},
        }
    """
    status = {}

    for branch in BRANCHES:
        # List contents of branch dir on gh-pages
        try:
            result = subprocess.run(
                ["gh", "api",
                 f"repos/{slug}/contents/{branch}?ref=gh-pages",
                 "--jq", ".[].name",
                 "--cache", "1m",
                 ],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                continue

            platform_dirs = [
                line.strip() for line in result.stdout.strip().split("\n")
                if line.strip() and not line.strip().endswith(".html")
            ]
        except Exception:
            continue

        branch_status = {}
        for platform_id in platform_dirs:
            try:
                import base64
                result = subprocess.run(
                    ["gh", "api",
                     f"repos/{slug}/contents/{branch}/{platform_id}/results.json?ref=gh-pages",
                     "--jq", ".content",
                     "--cache", "1m",
                     ],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    continue

                content = base64.b64decode(result.stdout.strip()).decode("utf-8")
                data = json.loads(content)
                # Derive success from summary if top-level field is missing
                # (older results.json files don't have the success field)
                success = data.get("success")
                if success is None:
                    summary = data.get("summary", {})
                    if summary.get("total", 0) > 0:
                        success = summary.get("failed", 1) == 0

                branch_status[platform_id] = {
                    "success": success,
                    "commit_hash": data.get("commit_hash", ""),
                    "timestamp": data.get("timestamp", ""),
                }
            except Exception:
                continue

        if branch_status:
            status[branch] = branch_status

    return status


def _format_branch(branch_data: dict, local_head: str) -> str:
    """Format platform results for a branch cell, grouped by GPU/CPU."""
    if not branch_data:
        return "[dim]—[/dim]"

    # Split into GPU and CPU platforms
    gpu_platforms = {}
    cpu_platforms = {}
    for platform_id, info in sorted(branch_data.items()):
        if platform_id.endswith("-gpu"):
            gpu_platforms[platform_id] = info
        else:
            cpu_platforms[platform_id] = info

    lines = []

    for label, platforms in [("GPU", gpu_platforms), ("CPU", cpu_platforms)]:
        if not platforms:
            continue

        entries = []
        for platform_id, info in sorted(platforms.items()):
            success = info.get("success")
            commit = info.get("commit_hash", "")
            short = commit[:7] if commit else "?"

            if success is True:
                status = "[green]pass[/green]"
            elif success is False:
                status = "[bold red]FAIL[/bold red]"
            else:
                status = "[yellow]?[/yellow]"

            # Commit freshness
            if commit and local_head and commit == local_head:
                commit_tag = f"[dim]{short}[/dim]"
            else:
                commit_tag = f"[yellow]{short}[/yellow]"

            # Short OS name
            os_name = platform_id.replace("-gpu", "").replace("-cpu", "")
            os_name = os_name.replace("windows-portable", "wp").replace("windows", "win").replace("linux", "lnx").replace("macos", "mac")

            entries.append(f"{os_name} {status} {commit_tag}")

        label_style = "[bold magenta]GPU[/bold magenta]" if label == "GPU" else "[bold blue]CPU[/bold blue]"
        for entry in entries:
            lines.append(f"{label_style} {entry}")

    return "\n".join(lines) if lines else "[dim]—[/dim]"


def show_test_status() -> int:
    """Show test results status from gh-pages for all repos."""
    repos = _get_repo_slugs()
    if not repos:
        console.print("[red]No repos found in all_repos/[/red]")
        return 1

    console.print(f"[dim]Checking {len(repos)} repos...[/dim]")

    # Fetch gh-pages status in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_fetch_gh_pages_status, slug): (name, slug, path)
            for name, slug, path in repos
        }
        for future in as_completed(futures):
            name, slug, path = futures[future]
            try:
                results[name] = {
                    "slug": slug,
                    "path": path,
                    "status": future.result(),
                    "local_head": _get_local_head(path),
                    "local_branch": _get_local_branch(path),
                }
            except Exception as e:
                results[name] = {
                    "slug": slug,
                    "path": path,
                    "status": {},
                    "local_head": "",
                    "local_branch": "",
                    "error": str(e),
                }

    # Build table
    table = Table(title="Test Results (gh-pages)")
    table.add_column("Repo", style="cyan", max_width=24)
    table.add_column("Branch", style="white")
    table.add_column("dev", min_width=25)
    table.add_column("main", min_width=25)

    for name in sorted(results.keys()):
        info = results[name]
        status = info["status"]
        local_head = info["local_head"]
        local_branch = info.get("local_branch", "")

        dev_data = status.get("dev", {})
        main_data = status.get("main", {})

        dev_summary = _format_branch(dev_data, local_head)
        main_summary = _format_branch(main_data, local_head)

        short_name = name.replace("ComfyUI-", "")
        branch_display = f"[dim]{local_branch}[/dim]" if local_branch else "[dim]?[/dim]"

        table.add_row(short_name, branch_display, dev_summary, main_summary)

    console.print(table)

    # Show legend
    console.print()
    console.print("[dim]Commit hashes: [/dim][dim]grey[/dim][dim] = matches local HEAD, [/dim][yellow]yellow[/yellow][dim] = stale[/dim]")

    return 0
