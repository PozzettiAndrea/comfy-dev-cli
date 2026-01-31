"""Discord integration for 3D AI Watcher.

Handles:
- Sending candidates to user's DM
- Collecting approve/reject reactions
- Posting approved items to announcement channel
"""

import asyncio
import os
from dataclasses import dataclass

from rich.console import Console

console = Console()

# Check if discord.py is available
try:
    import discord
    from discord import Embed, Color
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    console.print("[yellow]discord.py not installed. Run: pip install discord.py[/yellow]")


@dataclass
class ReviewResult:
    """Result of reviewing an item."""
    item_id: str
    url: str
    approved: bool
    skipped: bool = False


def create_embed(item, matched_keyword: str = None) -> "Embed":
    """Create a Discord embed for an item."""
    if not DISCORD_AVAILABLE:
        return None

    # Color by source
    colors = {
        "github": Color.from_rgb(36, 41, 46),
        "twitter": Color.from_rgb(29, 161, 242),
        "reddit": Color.from_rgb(255, 69, 0),
    }
    color = colors.get(item.source, Color.blurple())

    embed = Embed(
        title=item.title[:256],
        description=item.description[:2000] if item.description else "No description",
        url=item.url,
        color=color
    )

    # Add source info
    source_display = {
        "github": f"GitHub ({getattr(item, 'org', 'unknown')})",
        "twitter": f"Twitter (@{getattr(item, 'author', 'unknown')})",
        "reddit": f"Reddit (r/{getattr(item, 'subreddit', 'unknown')})",
    }
    embed.add_field(
        name="Source",
        value=source_display.get(item.source, item.source),
        inline=True
    )

    # Add stats if available
    if hasattr(item, 'stars') and item.stars:
        embed.add_field(name="Stars", value=str(item.stars), inline=True)
    if hasattr(item, 'score') and item.score:
        embed.add_field(name="Score", value=str(item.score), inline=True)

    # Add matched keyword
    if matched_keyword:
        embed.add_field(name="Matched", value=matched_keyword, inline=True)

    embed.set_footer(text=f"React: ✅ approve | ❌ reject | ⏭️ skip")

    return embed


async def send_for_review(client: "discord.Client", user_id: int, items: list,
                          keywords_matched: dict = None) -> list:
    """Send items to user's DM for review.

    Args:
        client: Discord client
        user_id: User's Discord ID
        items: List of items to review
        keywords_matched: Dict mapping item_id to matched keyword

    Returns:
        List of ReviewResult objects
    """
    if not DISCORD_AVAILABLE:
        console.print("[red]Discord not available[/red]")
        return []

    keywords_matched = keywords_matched or {}
    results = []

    try:
        user = await client.fetch_user(user_id)
        dm_channel = await user.create_dm()
    except Exception as e:
        console.print(f"[red]Failed to create DM channel: {e}[/red]")
        return []

    # Send intro message
    await dm_channel.send(
        f"**🔍 3D AI Watcher - {len(items)} items to review**\n"
        f"React with ✅ to approve, ❌ to reject, or ⏭️ to skip."
    )

    for item in items:
        keyword = keywords_matched.get(item.id)
        embed = create_embed(item, keyword)

        try:
            msg = await dm_channel.send(embed=embed)

            # Add reactions
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            await msg.add_reaction("⏭️")

            # Wait for reaction (timeout: 5 minutes per item)
            def check(reaction, reactor):
                return (
                    reactor.id == user_id and
                    reaction.message.id == msg.id and
                    str(reaction.emoji) in ["✅", "❌", "⏭️"]
                )

            try:
                reaction, _ = await client.wait_for("reaction_add", timeout=300, check=check)
                emoji = str(reaction.emoji)

                if emoji == "✅":
                    results.append(ReviewResult(item.id, item.url, approved=True))
                    await msg.add_reaction("📨")  # Mark as will be posted
                elif emoji == "❌":
                    results.append(ReviewResult(item.id, item.url, approved=False))
                else:
                    results.append(ReviewResult(item.id, item.url, approved=False, skipped=True))

            except asyncio.TimeoutError:
                # Auto-skip on timeout
                results.append(ReviewResult(item.id, item.url, approved=False, skipped=True))
                await msg.add_reaction("⏰")  # Mark as timed out

        except Exception as e:
            console.print(f"[red]Error sending item: {e}[/red]")
            continue

    # Send summary
    approved_count = sum(1 for r in results if r.approved)
    rejected_count = sum(1 for r in results if not r.approved and not r.skipped)
    skipped_count = sum(1 for r in results if r.skipped)

    await dm_channel.send(
        f"**Review complete!**\n"
        f"✅ Approved: {approved_count}\n"
        f"❌ Rejected: {rejected_count}\n"
        f"⏭️ Skipped: {skipped_count}"
    )

    return results


async def post_to_channel(client: "discord.Client", channel_id: int, items: list,
                          keywords_matched: dict = None):
    """Post approved items to the announcement channel.

    Args:
        client: Discord client
        channel_id: Channel ID to post to
        items: List of approved items
        keywords_matched: Dict mapping item_id to matched keyword
    """
    if not DISCORD_AVAILABLE:
        return

    if not items:
        return

    keywords_matched = keywords_matched or {}

    try:
        channel = await client.fetch_channel(channel_id)
    except Exception as e:
        console.print(f"[red]Failed to fetch channel: {e}[/red]")
        return

    for item in items:
        keyword = keywords_matched.get(item.id)
        embed = create_embed(item, keyword)

        # Remove the footer (no need for review instructions)
        if embed:
            embed.set_footer(text=f"Source: {item.source}")

        try:
            await channel.send(embed=embed)
            console.print(f"[green]Posted: {item.title}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to post {item.title}: {e}[/red]")


class WatcherBot(discord.Client):
    """Discord client for 3D AI Watcher."""

    def __init__(self, items: list, user_id: int, channel_id: int, keywords_matched: dict = None):
        intents = discord.Intents.default()
        intents.reactions = True
        intents.dm_messages = True
        super().__init__(intents=intents)

        self.items = items
        self.user_id = user_id
        self.channel_id = channel_id
        self.keywords_matched = keywords_matched or {}
        self.results = []
        self.approved_items = []

    async def on_ready(self):
        console.print(f"[green]Discord bot ready as {self.user}[/green]")

        # Send items for review
        self.results = await send_for_review(
            self, self.user_id, self.items, self.keywords_matched
        )

        # Collect approved items
        approved_urls = {r.url for r in self.results if r.approved}
        self.approved_items = [item for item in self.items if item.url in approved_urls]

        # Post approved items to channel
        if self.approved_items and self.channel_id:
            await post_to_channel(
                self, self.channel_id, self.approved_items, self.keywords_matched
            )

        # Done - close the bot
        await self.close()


def run_discord_review(items: list, bot_token: str, user_id: int, channel_id: int,
                       keywords_matched: dict = None) -> tuple:
    """Run the Discord review process.

    Args:
        items: List of items to review
        bot_token: Discord bot token
        user_id: User's Discord ID (for DMs)
        channel_id: Channel ID for approved posts
        keywords_matched: Dict mapping item_id to matched keyword

    Returns:
        (results, approved_items) tuple
    """
    if not DISCORD_AVAILABLE:
        console.print("[red]discord.py not installed. Run: pip install discord.py[/red]")
        return [], []

    if not items:
        console.print("[yellow]No items to review[/yellow]")
        return [], []

    bot = WatcherBot(items, user_id, channel_id, keywords_matched)

    try:
        bot.run(bot_token)
    except Exception as e:
        console.print(f"[red]Discord error: {e}[/red]")
        return [], []

    return bot.results, bot.approved_items
