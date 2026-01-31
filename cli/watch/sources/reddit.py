"""Reddit source for 3D AI Watcher.

Fetches posts from subreddits and users via Reddit JSON API (no auth needed).
"""

import json
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class RedditItem:
    """A Reddit item (post)."""
    id: str
    title: str
    description: str
    url: str
    source: str = "reddit"
    item_type: str = "post"
    subreddit: str = ""
    author: str = ""
    score: int = 0
    created_at: str = ""


def fetch_subreddit_posts(subreddit: str, limit: int = 50, since_days: int = 7) -> list:
    """Fetch recent posts from a subreddit.

    Args:
        subreddit: Subreddit name (without r/)
        limit: Max posts to fetch
        since_days: Only return posts from the last N days

    Returns:
        List of RedditItem objects
    """
    items = []
    cutoff = datetime.now() - timedelta(days=since_days)

    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"

    try:
        req = Request(url, headers={
            "User-Agent": "3D-AI-Watcher/1.0"
        })

        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        posts = data.get("data", {}).get("children", [])

        for post_wrapper in posts:
            post = post_wrapper.get("data", {})

            # Check age
            created_utc = post.get("created_utc", 0)
            created_dt = datetime.fromtimestamp(created_utc)
            if created_dt < cutoff:
                continue

            # Skip removed/deleted posts
            if post.get("removed_by_category") or post.get("author") == "[deleted]":
                continue

            item = RedditItem(
                id=f"reddit:{post['id']}",
                title=post.get("title", ""),
                description=post.get("selftext", "")[:500] or post.get("url", ""),
                url=f"https://reddit.com{post.get('permalink', '')}",
                subreddit=subreddit,
                author=post.get("author", ""),
                score=post.get("score", 0),
                created_at=created_dt.isoformat()
            )
            items.append(item)

    except Exception as e:
        console.print(f"[dim]Reddit r/{subreddit} error: {e}[/dim]")

    return items


def fetch_user_posts(username: str, limit: int = 25, since_days: int = 30) -> list:
    """Fetch recent posts from a Reddit user.

    Args:
        username: Reddit username (without u/)
        limit: Max posts to fetch
        since_days: Only return posts from the last N days

    Returns:
        List of RedditItem objects
    """
    items = []
    cutoff = datetime.now() - timedelta(days=since_days)

    url = f"https://www.reddit.com/user/{username}/submitted.json?limit={limit}"

    try:
        req = Request(url, headers={
            "User-Agent": "3D-AI-Watcher/1.0"
        })

        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        posts = data.get("data", {}).get("children", [])

        for post_wrapper in posts:
            post = post_wrapper.get("data", {})

            # Check age
            created_utc = post.get("created_utc", 0)
            created_dt = datetime.fromtimestamp(created_utc)
            if created_dt < cutoff:
                continue

            item = RedditItem(
                id=f"reddit:{post['id']}",
                title=post.get("title", ""),
                description=post.get("selftext", "")[:500] or post.get("url", ""),
                url=f"https://reddit.com{post.get('permalink', '')}",
                subreddit=post.get("subreddit", ""),
                author=username,
                score=post.get("score", 0),
                created_at=created_dt.isoformat()
            )
            items.append(item)

    except Exception as e:
        console.print(f"[dim]Reddit u/{username} error: {e}[/dim]")

    return items


def fetch_all_reddit(subreddits: list, users: list, since_days: int = 7) -> list:
    """Fetch posts from all configured subreddits and users.

    Args:
        subreddits: List of subreddit names to check
        users: List of usernames to check
        since_days: Look back this many days

    Returns:
        List of RedditItem objects
    """
    all_items = []

    for subreddit in subreddits:
        console.print(f"[dim]Checking Reddit: r/{subreddit}...[/dim]")
        items = fetch_subreddit_posts(subreddit, since_days=since_days)
        all_items.extend(items)

    for username in users:
        console.print(f"[dim]Checking Reddit: u/{username}...[/dim]")
        items = fetch_user_posts(username, since_days=since_days)
        all_items.extend(items)

    console.print(f"[dim]Found {len(all_items)} posts from Reddit[/dim]")
    return all_items
