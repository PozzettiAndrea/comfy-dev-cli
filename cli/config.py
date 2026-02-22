"""Configuration and repo loading for repo-tools."""

import json
import os
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import yaml
from dotenv import load_dotenv

# Paths - use fixed location so it works when installed globally
ROOT_DIR = Path.home() / "coding-scripts"
CLI_DIR = ROOT_DIR / "cli"
PRIVATE_DIR = ROOT_DIR / "private"

# Load .env file from private directory
ENV_FILE = PRIVATE_DIR / ".env"
load_dotenv(ENV_FILE)

LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"
COMMAND_CENTER_DIR = DATA_DIR / "command-center"
REPO_DATA_FILE = COMMAND_CENTER_DIR / "repo_data.json"
REPO_NOTES_FILE = COMMAND_CENTER_DIR / "repo_notes.csv"
NOTES_DIR = ROOT_DIR / "notes"

# Clone target directories (sibling to coding-scripts)
HOME_DIR = Path.home()
# On Windows, use Desktop; on Linux, use home directory
if platform.system() == "Windows":
    INSTALL_DIR = HOME_DIR / "Desktop"
else:
    INSTALL_DIR = HOME_DIR
ALL_REPOS_DIR = INSTALL_DIR / "all_repos"
WHEEL_REPOS_DIR = INSTALL_DIR / "wheel_repos"
UTILS_REPOS_DIR = INSTALL_DIR / "utils"
ISSUES_DIR = INSTALL_DIR / "issues"

# Central directory for uv virtual environments (like conda's envs/)
CT_ENVS_DIR = HOME_DIR / "ct-envs"

# Command name (configurable via command_name.txt)
_COMMAND_NAME_FILE = ROOT_DIR / "comfy-dev-cli" / "command_name.txt"
COMMAND_NAME = _COMMAND_NAME_FILE.read_text().strip() if _COMMAND_NAME_FILE.exists() else "ct"

# GitHub owner - load from env var or identity.yml
def _load_github_owner() -> str:
    if os.environ.get("GITHUB_OWNER"):
        return os.environ["GITHUB_OWNER"]
    identity_file = PRIVATE_DIR / "identity.yml"
    if identity_file.exists():
        with open(identity_file) as f:
            identity = yaml.safe_load(f)
            return identity.get("github_owner", "")
    return ""

GITHUB_OWNER = _load_github_owner()


@dataclass
class Repo:
    """Represents a GitHub repository."""
    name: str
    full_name: str
    category: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    open_prs: int = 0
    watchers: int = 0
    url: str = ""
    visibility: str = "public"  # "public" or "private"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.full_name}"

    @property
    def is_private(self) -> bool:
        return self.visibility == "private"


def load_repos_from_json() -> list[Repo]:
    """Load repos from repo_data.json if it exists."""
    if not REPO_DATA_FILE.exists():
        return []

    with open(REPO_DATA_FILE) as f:
        data = json.load(f)

    # Handle nested structure: [{"timestamp": ..., "repositories": [...]}]
    if isinstance(data, list) and len(data) > 0:
        if "repositories" in data[0]:
            # Get the most recent snapshot
            data = data[0].get("repositories", [])

    repos = []
    for item in data:
        repos.append(Repo(
            name=item.get("name", ""),
            full_name=item.get("full_name", f"{GITHUB_OWNER}/{item.get('name', '')}"),
            category=item.get("category", ""),
            stars=item.get("stars", item.get("stargazers_count", 0)),
            forks=item.get("forks", item.get("forks_count", 0)),
            open_issues=item.get("open_issues", item.get("open_issues_count", 0)),
            open_prs=item.get("open_prs", 0),
            watchers=item.get("watchers", item.get("watchers_count", 0)),
            url=item.get("url", item.get("html_url", "")),
            visibility=item.get("visibility", "public"),
        ))
    return repos


def load_repos_from_csv() -> list[tuple[str, str, str]]:
    """Load repo names, categories, and visibility from repo_notes.csv.

    Returns list of (name, category, visibility) tuples.
    """
    if not REPO_NOTES_FILE.exists():
        return []

    with open(REPO_NOTES_FILE) as f:
        lines = f.readlines()

    # Skip header, parse: repo_name,category,visibility,notes
    repos = []
    for line in lines[1:]:
        parts = line.strip().split(",")
        name = parts[0] if len(parts) > 0 else ""
        category = parts[1] if len(parts) > 1 else ""
        visibility = parts[2] if len(parts) > 2 else "public"
        if name:
            repos.append((name, category, visibility))
    return repos


def get_all_repos() -> list[Repo]:
    """Get all repos, preferring JSON data but falling back to CSV."""
    repos = load_repos_from_json()
    if repos:
        return repos

    # Fallback to CSV
    csv_repos = load_repos_from_csv()
    return [
        Repo(name=name, full_name=f"{GITHUB_OWNER}/{name}", category=category, visibility=visibility)
        for name, category, visibility in csv_repos
    ]


def get_repo_config_map() -> dict[str, tuple[str, str]]:
    """Map repo name -> (config_name, folder_name) by scanning setup configs.

    Parses each *.yml in config/setup/ and extracts repo names from
    nodes_to_install URLs. Returns e.g.:
        {"ComfyUI-SAM3": ("sam3", "sam3"), "ComfyUI-HY-WorldPlay": ("world", "world")}
    """
    setup_dir = Path(__file__).parent.parent / "config" / "setup"
    mapping = {}
    for config_file in setup_dir.glob("*.yml"):
        with open(config_file) as f:
            config = yaml.safe_load(f)
        if not config:
            continue
        config_name = config_file.stem
        folder_name = config.get("folder_name", config_name)
        for node in config.get("nodes_to_install", []):
            if isinstance(node, dict):
                url = node.get("url", "")
            else:
                url = node
            if url:
                repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
                mapping[repo_name] = (config_name, folder_name)
    return mapping


def get_repos_by_category(category: str) -> list[Repo]:
    """Get repos filtered by category from CSV."""
    csv_repos = load_repos_from_csv()
    return [
        Repo(name=name, full_name=f"{GITHUB_OWNER}/{name}", category=cat, visibility=visibility)
        for name, cat, visibility in csv_repos
        if cat == category
    ]


def load_reddit_links() -> list[str]:
    """Load Reddit post URLs from reddit_links.txt."""
    if not REDDIT_LINKS_FILE.exists():
        return []

    with open(REDDIT_LINKS_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def refresh_repo_data() -> bool:
    """Fetch fresh repo data from GitHub and update repo_data.json."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return False

    from github import Github
    from datetime import datetime

    g = Github(token)
    csv_repos = load_repos_from_csv()
    if not csv_repos:
        # Fallback: get from existing JSON
        existing = load_repos_from_json()
        csv_repos = [(r.name, r.category, r.visibility) for r in existing]

    repositories = []
    for name, category, visibility in csv_repos:
        try:
            repo = g.get_repo(f"{GITHUB_OWNER}/{name}")
            open_prs = repo.get_pulls(state='open').totalCount
            # Use visibility from CSV, or detect from API
            actual_visibility = "private" if repo.private else "public"
            repositories.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "category": category,
                "visibility": actual_visibility,
                "url": repo.html_url,
                "description": repo.description or "",
                "stars": repo.stargazers_count,
                "open_issues": repo.open_issues_count,
                "open_prs": open_prs,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "last_updated": repo.updated_at.isoformat(),
                "created_at": repo.created_at.isoformat(),
                "language": repo.language or "",
            })
        except Exception:
            continue

    data = [{
        "timestamp": datetime.now().isoformat(),
        "repositories": repositories,
    }]

    REPO_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPO_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return True


REPO_STATS_FILE = COMMAND_CENTER_DIR / "repo_stats.json"

# Cached stats loaded at startup
_cached_repo_stats = {}


def _fetch_single_repo_stats(repo_name: str, token: str) -> tuple[str, dict]:
    """Fetch stats for a single repo. Used by thread pool."""
    import httpx
    from github import Github

    repo_stats = {
        "discussions": 0, "unanswered": 0, "waiting_on_op": 0,
        "active_forks": 0, "open_prs": 0,
        "has_tests": None, "tests_passing_main": None, "tests_passing_dev": None,
        "tests_main_url": None, "tests_dev_url": None
    }

    discussion_query = """
    query($owner: String!, $name: String!, $first: Int!) {
      repository(owner: $owner, name: $name) {
        discussions(first: $first, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            title
            url
            createdAt
            author { login }
            category { name }
            comments { totalCount }
            answerChosenAt
          }
        }
      }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Fetch discussions via GraphQL
    discussions_list = []
    try:
        response = httpx.post(
            "https://api.github.com/graphql",
            json={
                "query": discussion_query,
                "variables": {
                    "owner": GITHUB_OWNER,
                    "name": repo_name,
                    "first": 100,
                },
            },
            headers=headers,
            timeout=30,
        )
        data = response.json()

        if "errors" not in data:
            discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
            for d in discussions:
                is_unanswered = d["comments"]["totalCount"] == 0 and d["answerChosenAt"] is None
                discussions_list.append({
                    "title": d["title"],
                    "url": d["url"],
                    "author": d["author"]["login"] if d["author"] else "unknown",
                    "category": d["category"]["name"] if d["category"] else "",
                    "comments": d["comments"]["totalCount"],
                    "created": d["createdAt"][:10],
                    "unanswered": is_unanswered,
                })
            repo_stats["discussions"] = len(discussions_list)
            repo_stats["unanswered"] = sum(1 for d in discussions_list if d["unanswered"])
            repo_stats["discussions_list"] = discussions_list
    except Exception:
        pass

    # Fetch waiting-on-OP issues and active forks via REST API
    try:
        g = Github(token)
        gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo_name}")

        # Count open PRs
        repo_stats["open_prs"] = gh_repo.get_pulls(state="open").totalCount

        # Fetch issues with details
        issues_list = []
        for issue in gh_repo.get_issues(state="open"):
            if issue.pull_request:
                continue
            comments = list(issue.get_comments())
            waiting_on_op = comments and comments[-1].user.login == GITHUB_OWNER
            if waiting_on_op:
                repo_stats["waiting_on_op"] += 1
            issues_list.append({
                "title": issue.title,
                "url": issue.html_url,
                "number": issue.number,
                "author": issue.user.login,
                "created": issue.created_at.strftime("%Y-%m-%d"),
                "comments": issue.comments,
                "labels": [l.name for l in issue.labels],
                "waiting_on_op": waiting_on_op,
            })
        repo_stats["issues_list"] = issues_list

        # Check active forks (forks with commits ahead of parent)
        active_forks_list = []
        for fork in gh_repo.get_forks():
            try:
                comparison = gh_repo.compare(gh_repo.default_branch, f"{fork.owner.login}:{fork.default_branch}")
                if comparison.ahead_by > 0:
                    active_forks_list.append({
                        "owner": fork.owner.login,
                        "name": fork.full_name,
                        "url": fork.html_url,
                        "ahead_by": comparison.ahead_by,
                        "stars": fork.stargazers_count,
                    })
            except Exception:
                pass
        repo_stats["active_forks"] = len(active_forks_list)
        repo_stats["active_forks_list"] = active_forks_list

        # Check if tests exist (look for common test patterns)
        try:
            contents = gh_repo.get_contents("")
            root_names = [c.name.lower() for c in contents]

            # Check for tests/ directory or test files
            has_tests = False
            if "tests" in root_names or "test" in root_names:
                has_tests = True
            elif "pytest.ini" in root_names or "conftest.py" in root_names:
                has_tests = True
            else:
                # Check for test_*.py files in root
                for c in contents:
                    if c.name.startswith("test_") and c.name.endswith(".py"):
                        has_tests = True
                        break
            repo_stats["has_tests"] = has_tests
        except Exception:
            pass

        # Check tests passing for main branch
        try:
            workflows = gh_repo.get_workflow_runs(status="completed", branch="main")
            for run in workflows[:1]:
                repo_stats["tests_passing_main"] = (run.conclusion == "success")
                repo_stats["tests_main_url"] = run.html_url
                break
        except Exception:
            pass

        # Check tests passing for dev branch
        try:
            workflows = gh_repo.get_workflow_runs(status="completed", branch="dev")
            for run in workflows[:1]:
                repo_stats["tests_passing_dev"] = (run.conclusion == "success")
                repo_stats["tests_dev_url"] = run.html_url
                break
        except Exception:
            pass
    except Exception:
        pass

    return repo_name, repo_stats


def refresh_repo_stats(workers: int = 8) -> dict:
    """Fetch per-repo stats using thread pool and cache to file.

    Returns dict mapping repo name to {"discussions": int, "unanswered": int, "waiting_on_op": int}
    """
    global _cached_repo_stats
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {}

    repos = get_all_repos()
    stats = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_fetch_single_repo_stats, repo.name, token): repo.name
            for repo in repos
        }

        for future in tqdm(as_completed(futures), total=len(repos), desc="Fetching repo stats"):
            repo_name, repo_stats = future.result()
            stats[repo_name] = repo_stats

    # Cache to file
    with open(REPO_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

    _cached_repo_stats = stats
    return stats


def get_repo_stats() -> dict:
    """Get cached repo stats. Call refresh_repo_stats() first during startup."""
    global _cached_repo_stats

    if _cached_repo_stats:
        return _cached_repo_stats

    # Try loading from file
    if REPO_STATS_FILE.exists():
        with open(REPO_STATS_FILE) as f:
            _cached_repo_stats = json.load(f)
        return _cached_repo_stats

    return {}


# Environment variables
def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


def verify_github_token(token: str) -> bool:
    """Verify that a GitHub token is valid by making a test API call."""
    import httpx
    try:
        response = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return response.status_code == 200
    except Exception:
        return False


def save_github_token(token: str) -> None:
    """Save GitHub token to .env file."""
    env_content = ""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            env_content = f.read()

    # Update or add GITHUB_TOKEN
    lines = env_content.strip().split("\n") if env_content.strip() else []
    new_lines = [line for line in lines if not line.startswith("GITHUB_TOKEN=")]
    new_lines.append(f"GITHUB_TOKEN={token}")

    with open(ENV_FILE, "w") as f:
        f.write("\n".join(new_lines) + "\n")

    # Also set in current environment
    os.environ["GITHUB_TOKEN"] = token


def require_github_token() -> str:
    """Ensure a valid GitHub token is available, prompting if needed.

    Returns the token if valid, or raises SystemExit if user cancels.
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()
    token = get_github_token()

    if token:
        return token

    console.print("[yellow]No GitHub token found.[/yellow]")
    console.print("You can create a token at: https://github.com/settings/tokens")
    console.print("Required scopes: repo (for private repos) or public_repo (for public only)\n")

    while True:
        token = Prompt.ask("Enter your GitHub token (or 'q' to quit)")

        if token.lower() == 'q':
            raise SystemExit("Cancelled.")

        if not token.strip():
            console.print("[red]Token cannot be empty.[/red]")
            continue

        console.print("Verifying token...", end=" ")
        if verify_github_token(token):
            console.print("[green]Valid![/green]")
            save_github_token(token)
            console.print(f"[dim]Token saved to {ENV_FILE}[/dim]\n")
            return token
        else:
            console.print("[red]Invalid token. Please try again.[/red]")


def get_openrouter_key() -> Optional[str]:
    """Get OpenRouter API key from environment."""
    return os.environ.get("OPENROUTER_API_KEY")


def get_reddit_credentials() -> dict:
    """Get Reddit API credentials from environment."""
    return {
        "client_id": os.environ.get("REDDIT_CLIENT_ID"),
        "client_secret": os.environ.get("REDDIT_CLIENT_SECRET"),
        "user_agent": os.environ.get("REDDIT_USER_AGENT", "repo-tools/1.0"),
    }


# 3D Index Configuration
_3D_INDEX_CONFIG = None
_3D_INDEX_CONFIG_FILE = Path(__file__).parent / "3d_index_config.yml"


def get_3d_index_config() -> dict:
    """Load 3D index configuration from YAML file."""
    global _3D_INDEX_CONFIG
    if _3D_INDEX_CONFIG is None:
        if _3D_INDEX_CONFIG_FILE.exists():
            import yaml
            with open(_3D_INDEX_CONFIG_FILE) as f:
                _3D_INDEX_CONFIG = yaml.safe_load(f)
        else:
            _3D_INDEX_CONFIG = {}
    return _3D_INDEX_CONFIG


# =============================================================================
# Logging Configuration
# =============================================================================

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

_logging_initialized = False


def setup_logging(command_name: str = "ct") -> logging.Logger:
    """Set up logging to file in coding-scripts/logs directory.

    Args:
        command_name: Name of the command being run (used in log filename)

    Returns:
        Configured logger instance
    """
    global _logging_initialized

    # Create logs directory if it doesn't exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Create log filename with time (HHMM format)
    time_str = datetime.now().strftime("%H%M")
    log_file = LOGS_DIR / f"{command_name}_{time_str}.log"

    # Configure root logger
    logger = logging.getLogger("ct")

    # Only configure once
    if _logging_initialized:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Also log errors to stderr (but don't duplicate Rich console output)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stderr_handler)

    _logging_initialized = True
    logger.info(f"Logging initialized for command: {command_name}")

    return logger


def get_logger(name: str = "ct") -> logging.Logger:
    """Get a logger instance. Call setup_logging() first."""
    return logging.getLogger(f"ct.{name}" if name != "ct" else "ct")
