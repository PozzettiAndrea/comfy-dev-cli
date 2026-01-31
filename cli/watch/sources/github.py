"""GitHub source for 3D AI Watcher.

Monitors GitHub orgs for new repos and releases.
"""

import json
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class GitHubItem:
    """A GitHub item (repo or release)."""
    id: str
    title: str
    description: str
    url: str
    source: str = "github"
    item_type: str = "repo"  # "repo" or "release"
    org: str = ""
    stars: int = 0
    created_at: str = ""
    readme: str = ""


def fetch_org_repos(org: str, token: str = None, since_days: int = 30) -> list:
    """Fetch repos from a GitHub org created/updated recently.

    Args:
        org: GitHub organization name
        token: Optional GitHub token for higher rate limits
        since_days: Only return repos created/updated in the last N days

    Returns:
        List of GitHubItem objects
    """
    items = []
    cutoff = datetime.now() - timedelta(days=since_days)

    headers = {"User-Agent": "3D-AI-Watcher"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?sort=updated&per_page=100&page={page}"
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as resp:
                repos = json.loads(resp.read())
        except HTTPError as e:
            if e.code == 404:
                # Org not found, try as user
                url = f"https://api.github.com/users/{org}/repos?sort=updated&per_page=100&page={page}"
                try:
                    req = Request(url, headers=headers)
                    with urlopen(req, timeout=30) as resp:
                        repos = json.loads(resp.read())
                except Exception:
                    break
            else:
                console.print(f"[dim]GitHub API error for {org}: {e.code}[/dim]")
                break
        except Exception as e:
            console.print(f"[dim]Error fetching {org}: {e}[/dim]")
            break

        if not repos:
            break

        for repo in repos:
            # Check if recently updated
            updated = repo.get("updated_at", "") or repo.get("pushed_at", "")
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if updated_dt.replace(tzinfo=None) < cutoff:
                        continue
                except Exception:
                    pass

            # Skip forks unless they have significant stars
            if repo.get("fork") and repo.get("stargazers_count", 0) < 10:
                continue

            item = GitHubItem(
                id=f"github:{repo['full_name']}",
                title=repo["name"],
                description=repo.get("description") or "",
                url=repo["html_url"],
                org=org,
                stars=repo.get("stargazers_count", 0),
                created_at=repo.get("created_at", ""),
                item_type="repo"
            )
            items.append(item)

        page += 1
        if page > 5:  # Limit pages
            break

    return items


def fetch_repo_readme(owner: str, repo: str, token: str = None) -> str:
    """Fetch README content for a repo."""
    headers = {"User-Agent": "3D-AI-Watcher"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for branch in ["main", "master"]:
        for fname in ["README.md", "readme.md", "Readme.md"]:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
            try:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=10) as resp:
                    return resp.read().decode("utf-8", errors="replace")[:5000]
            except:
                continue
    return ""


def fetch_org_releases(org: str, token: str = None, since_days: int = 7) -> list:
    """Fetch recent releases from repos in an org.

    Note: This is more expensive (requires fetching each repo's releases).
    Only call for important orgs.
    """
    # For now, skip release checking to keep API usage low
    # Can be enabled later if needed
    return []


def fetch_all_github(orgs: list, token: str = None, since_days: int = 30, max_workers: int = 5) -> list:
    """Fetch new items from all configured GitHub orgs.

    Args:
        orgs: List of org/user names to check
        token: Optional GitHub token
        since_days: Look back this many days
        max_workers: Parallel workers for fetching

    Returns:
        List of GitHubItem objects
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_items = []

    def fetch_org(org):
        console.print(f"[dim]Checking GitHub: {org}...[/dim]")
        return fetch_org_repos(org, token, since_days)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_org, org): org for org in orgs}
        for future in as_completed(futures):
            items = future.result()
            all_items.extend(items)

    console.print(f"[dim]Found {len(all_items)} repos from {len(orgs)} orgs[/dim]")
    return all_items
