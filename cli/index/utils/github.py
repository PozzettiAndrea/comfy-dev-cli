"""GitHub utilities for 3D index generation."""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError


def extract_github_info(url_or_node):
    """Extract owner/repo from GitHub URL or node dict.

    Handles:
    - Direct URL strings
    - Node dicts with 'reference' or 'repository' keys

    Returns (owner, repo) tuple, or (None, None) if not found.
    """
    if isinstance(url_or_node, dict):
        url = url_or_node.get("reference", "") or url_or_node.get("repository", "") or ""
    else:
        url = url_or_node or ""

    if not url:
        return None, None

    match = re.search(r"github\.com/([^/]+)/([^/\s]+)", url)
    if match:
        owner = match.group(1)
        repo = match.group(2).replace(".git", "").rstrip("/")
        return owner, repo
    return None, None


def fetch_readme(owner, repo, timeout=10):
    """Fetch README content and branch from GitHub.

    Returns (readme_content, branch) tuple.
    """
    for branch in ["main", "master"]:
        for fname in ["README.md", "readme.md", "Readme.md"]:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
            try:
                with urlopen(url, timeout=timeout) as resp:
                    return resp.read().decode("utf-8", errors="replace"), branch
            except:
                continue
    return "", "main"


def fetch_github_stats(stats_url, timeout=30):
    """Fetch star counts from ComfyUI-Manager github-stats.json."""
    req = Request(stats_url)
    with urlopen(req, timeout=timeout) as resp:
        import json
        return json.loads(resp.read())


def fetch_repo_updated_at(owner, repo, timeout=10):
    """Fetch last updated date from GitHub API."""
    import json
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        req = Request(url, headers={"User-Agent": "ComfyUI-3D-Index"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("pushed_at", "")
    except Exception:
        return ""
