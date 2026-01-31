"""Twitter/X source for 3D AI Watcher.

Uses nitter instances to fetch tweets without requiring Twitter API.
"""

import re
import json
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from dataclasses import dataclass
from html.parser import HTMLParser

from rich.console import Console

console = Console()


@dataclass
class TwitterItem:
    """A Twitter item (tweet)."""
    id: str
    title: str
    description: str
    url: str
    source: str = "twitter"
    item_type: str = "tweet"
    author: str = ""
    created_at: str = ""


# Nitter instances to try (some may be down)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.cz",
]


class NitterParser(HTMLParser):
    """Parse tweets from nitter HTML."""

    def __init__(self):
        super().__init__()
        self.tweets = []
        self.current_tweet = None
        self.in_tweet_content = False
        self.in_tweet_date = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Tweet container
        if tag == "div" and "timeline-item" in attrs_dict.get("class", ""):
            self.current_tweet = {"text": "", "date": "", "link": ""}

        # Tweet content
        if tag == "div" and "tweet-content" in attrs_dict.get("class", ""):
            self.in_tweet_content = True

        # Tweet link
        if tag == "a" and "tweet-link" in attrs_dict.get("class", ""):
            href = attrs_dict.get("href", "")
            if self.current_tweet and href:
                self.current_tweet["link"] = href

        # Tweet date
        if tag == "span" and "tweet-date" in attrs_dict.get("class", ""):
            self.in_tweet_date = True

    def handle_endtag(self, tag):
        if tag == "div" and self.in_tweet_content:
            self.in_tweet_content = False

        if tag == "span" and self.in_tweet_date:
            self.in_tweet_date = False

        if tag == "div" and self.current_tweet:
            if self.current_tweet.get("text") and self.current_tweet.get("link"):
                self.tweets.append(self.current_tweet)
            self.current_tweet = None

    def handle_data(self, data):
        if self.in_tweet_content and self.current_tweet:
            self.current_tweet["text"] += data.strip() + " "

        if self.in_tweet_date and self.current_tweet:
            self.current_tweet["date"] = data.strip()


def fetch_nitter_timeline(username: str, instance: str = None) -> list:
    """Fetch tweets from a user via nitter.

    Args:
        username: Twitter username (without @)
        instance: Specific nitter instance to use

    Returns:
        List of TwitterItem objects
    """
    instances = [instance] if instance else NITTER_INSTANCES
    items = []

    for nitter_url in instances:
        try:
            url = f"{nitter_url}/{username}"
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            with urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # Parse HTML for tweets
            parser = NitterParser()
            parser.feed(html)

            for tweet in parser.tweets[:20]:  # Limit to 20 most recent
                # Convert nitter link to Twitter link
                link = tweet["link"]
                if link.startswith("/"):
                    twitter_url = f"https://twitter.com{link}"
                else:
                    twitter_url = link

                # Extract tweet ID from URL
                tweet_id_match = re.search(r"/status/(\d+)", link)
                tweet_id = tweet_id_match.group(1) if tweet_id_match else link

                item = TwitterItem(
                    id=f"twitter:{tweet_id}",
                    title=f"@{username}",
                    description=tweet["text"].strip()[:500],
                    url=twitter_url,
                    author=username,
                    created_at=tweet.get("date", "")
                )
                items.append(item)

            if items:
                break  # Successfully got tweets, don't try other instances

        except HTTPError as e:
            console.print(f"[dim]Nitter {nitter_url} returned {e.code} for @{username}[/dim]")
            continue
        except Exception as e:
            console.print(f"[dim]Nitter {nitter_url} error: {e}[/dim]")
            continue

    return items


def fetch_all_twitter(accounts: list) -> list:
    """Fetch tweets from all configured accounts.

    Args:
        accounts: List of Twitter usernames to check

    Returns:
        List of TwitterItem objects
    """
    all_items = []

    for username in accounts:
        console.print(f"[dim]Checking Twitter: @{username}...[/dim]")
        items = fetch_nitter_timeline(username)
        all_items.extend(items)

    console.print(f"[dim]Found {len(all_items)} tweets from {len(accounts)} accounts[/dim]")
    return all_items
