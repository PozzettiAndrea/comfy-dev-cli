"""Main entry point for 3D AI Watcher CLI."""

import os
import yaml
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

CONFIG_FILE = Path(__file__).parent.parent.parent / "3d_watch_config.yml"


def load_config() -> dict:
    """Load watcher configuration from YAML file."""
    if not CONFIG_FILE.exists():
        console.print(f"[red]Config file not found: {CONFIG_FILE}[/red]")
        return {}

    with open(CONFIG_FILE) as f:
        config = yaml.safe_load(f)

    # Substitute environment variables
    def substitute_env(obj):
        if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            return os.environ.get(var_name, "")
        elif isinstance(obj, dict):
            return {k: substitute_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_env(item) for item in obj]
        return obj

    return substitute_env(config)


def run_watch(dry_run: bool = False, sources: str = None, days: int = 30):
    """Run the 3D AI watcher.

    Args:
        dry_run: If True, show what would be sent but don't post to Discord
        sources: Comma-separated list of sources to check (github,twitter,reddit)
        days: Look back this many days
    """
    from .state import load_state, save_state, is_seen, mark_seen, mark_approved, mark_rejected
    from .filter import is_3d_relevant
    from .sources.github import fetch_all_github, fetch_repo_readme
    from .sources.twitter import fetch_all_twitter
    from .sources.reddit import fetch_all_reddit

    config = load_config()
    if not config:
        return

    state = load_state()

    # Parse sources filter
    source_filter = None
    if sources:
        source_filter = [s.strip().lower() for s in sources.split(",")]

    # Get keywords from config
    keywords_config = config.get("keywords", {})
    include_keywords = keywords_config.get("include", [])
    exclude_keywords = keywords_config.get("exclude", [])

    all_items = []
    keywords_matched = {}

    # Fetch from GitHub
    github_config = config.get("sources", {}).get("github", {})
    if github_config.get("enabled") and (not source_filter or "github" in source_filter):
        console.print("\n[bold cyan]Checking GitHub...[/bold cyan]")
        orgs = github_config.get("orgs", [])
        github_token = os.environ.get("GITHUB_TOKEN")

        items = fetch_all_github(orgs, github_token, since_days=days)

        # Two-pass filtering: first by title/description (fast), then fetch README only for candidates
        candidates = []
        for item in items:
            if is_seen(state, "github", item.id):
                continue

            # Quick filter by title/description only
            is_relevant, keyword = is_3d_relevant(
                item.title, item.description, "",
                include_keywords, exclude_keywords
            )

            if is_relevant:
                candidates.append((item, keyword))
                mark_seen(state, "github", item.id)

        console.print(f"[dim]Pre-filtered to {len(candidates)} candidates[/dim]")

        # Add candidates to results (skip README fetch for speed)
        for item, keyword in candidates:
            all_items.append(item)
            keywords_matched[item.id] = keyword

    # Fetch from Twitter
    twitter_config = config.get("sources", {}).get("twitter", {})
    if twitter_config.get("enabled") and (not source_filter or "twitter" in source_filter):
        console.print("\n[bold cyan]Checking Twitter...[/bold cyan]")
        accounts = twitter_config.get("accounts", [])

        items = fetch_all_twitter(accounts)

        for item in items:
            if is_seen(state, "twitter", item.id):
                continue

            is_relevant, keyword = is_3d_relevant(
                item.title, item.description, "",
                include_keywords, exclude_keywords
            )

            if is_relevant:
                all_items.append(item)
                keywords_matched[item.id] = keyword
                mark_seen(state, "twitter", item.id)

    # Fetch from Reddit
    reddit_config = config.get("sources", {}).get("reddit", {})
    if reddit_config.get("enabled") and (not source_filter or "reddit" in source_filter):
        console.print("\n[bold cyan]Checking Reddit...[/bold cyan]")
        subreddits = reddit_config.get("subreddits", [])
        users = reddit_config.get("users", [])

        items = fetch_all_reddit(subreddits, users, since_days=days)

        for item in items:
            if is_seen(state, "reddit", item.id):
                continue

            is_relevant, keyword = is_3d_relevant(
                item.title, item.description, "",
                include_keywords, exclude_keywords
            )

            if is_relevant:
                all_items.append(item)
                keywords_matched[item.id] = keyword
                mark_seen(state, "reddit", item.id)

    # Save state (even if we don't proceed with Discord)
    save_state(state)

    # Summary
    console.print(f"\n[bold green]Found {len(all_items)} relevant items[/bold green]")

    if not all_items:
        console.print("[dim]No new 3D-related items found.[/dim]")
        return

    # Show table
    table = Table(title="Items to Review")
    table.add_column("Source", style="cyan")
    table.add_column("Title", max_width=40)
    table.add_column("Matched", style="yellow")
    table.add_column("URL", max_width=50)

    for item in all_items:
        table.add_row(
            item.source,
            item.title[:40],
            keywords_matched.get(item.id, ""),
            item.url[:50]
        )

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry run - not sending to Discord[/yellow]")
        return

    # Discord review
    discord_config = config.get("discord", {})
    bot_token = discord_config.get("bot_token")
    user_id = discord_config.get("user_id")
    channel_id = discord_config.get("channel_id")

    if not bot_token:
        console.print("[red]Discord bot token not configured[/red]")
        console.print("[dim]Set DISCORD_BOT_TOKEN env var or update 3d_watch_config.yml[/dim]")
        return

    if not user_id:
        console.print("[red]Discord user ID not configured[/red]")
        console.print("[dim]Update 3d_watch_config.yml with your Discord user ID[/dim]")
        return

    try:
        user_id = int(user_id)
        channel_id = int(channel_id) if channel_id else None
    except ValueError:
        console.print("[red]Invalid Discord IDs in config[/red]")
        return

    console.print("\n[bold cyan]Starting Discord review...[/bold cyan]")

    from .discord_bot import run_discord_review

    results, approved_items = run_discord_review(
        all_items, bot_token, user_id, channel_id, keywords_matched
    )

    # Update state with approvals/rejections
    state = load_state()
    for result in results:
        if result.approved:
            mark_approved(state, result.url)
        elif not result.skipped:
            mark_rejected(state, result.url)
    save_state(state)

    console.print(f"\n[green]Review complete! Approved {len(approved_items)} items.[/green]")


def show_status():
    """Show current watcher status."""
    from .state import load_state

    state = load_state()
    config = load_config()

    console.print("\n[bold]3D AI Watcher Status[/bold]\n")

    if state.last_run:
        console.print(f"Last run: {state.last_run}")
    else:
        console.print("Last run: Never")

    console.print(f"Approved items: {len(state.approved)}")
    console.print(f"Rejected items: {len(state.rejected)}")

    console.print("\n[bold]Seen items by source:[/bold]")
    console.print(f"  GitHub: {len(state.github.seen_ids)}")
    console.print(f"  Twitter: {len(state.twitter.seen_ids)}")
    console.print(f"  Reddit: {len(state.reddit.seen_ids)}")

    console.print("\n[bold]Configured sources:[/bold]")
    sources = config.get("sources", {})
    for source, cfg in sources.items():
        enabled = "✓" if cfg.get("enabled") else "✗"
        console.print(f"  [{enabled}] {source}")


def reset_state(source: str = None):
    """Reset watcher state.

    Args:
        source: Specific source to reset, or None for all
    """
    from .state import load_state, save_state, SourceState

    state = load_state()

    if source:
        if hasattr(state, source):
            setattr(state, source, SourceState())
            console.print(f"[green]Reset state for {source}[/green]")
        else:
            console.print(f"[red]Unknown source: {source}[/red]")
    else:
        from .state import WatchState
        state = WatchState()
        console.print("[green]Reset all state[/green]")

    save_state(state)
