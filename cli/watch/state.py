"""State management for 3D AI Watcher."""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict


STATE_FILE = Path(__file__).parent.parent.parent / "3d_watch_state.json"


@dataclass
class SourceState:
    """State for a single source."""
    last_checked: str = ""
    seen_ids: list = field(default_factory=list)


@dataclass
class WatchState:
    """Overall watcher state."""
    last_run: str = ""
    github: SourceState = field(default_factory=SourceState)
    twitter: SourceState = field(default_factory=SourceState)
    reddit: SourceState = field(default_factory=SourceState)
    huggingface: SourceState = field(default_factory=SourceState)
    approved: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    def to_dict(self):
        return {
            "last_run": self.last_run,
            "github": asdict(self.github),
            "twitter": asdict(self.twitter),
            "reddit": asdict(self.reddit),
            "huggingface": asdict(self.huggingface),
            "approved": self.approved,
            "rejected": self.rejected,
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.last_run = data.get("last_run", "")
        state.github = SourceState(**data.get("github", {}))
        state.twitter = SourceState(**data.get("twitter", {}))
        state.reddit = SourceState(**data.get("reddit", {}))
        state.huggingface = SourceState(**data.get("huggingface", {}))
        state.approved = data.get("approved", [])
        state.rejected = data.get("rejected", [])
        return state


def load_state() -> WatchState:
    """Load state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            return WatchState.from_dict(data)
        except Exception:
            pass
    return WatchState()


def save_state(state: WatchState):
    """Save state to file."""
    state.last_run = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


def mark_seen(state: WatchState, source: str, item_id: str):
    """Mark an item as seen."""
    source_state = getattr(state, source, None)
    if source_state and item_id not in source_state.seen_ids:
        source_state.seen_ids.append(item_id)
        # Keep list from growing too large (last 1000)
        if len(source_state.seen_ids) > 1000:
            source_state.seen_ids = source_state.seen_ids[-1000:]


def is_seen(state: WatchState, source: str, item_id: str) -> bool:
    """Check if an item has been seen."""
    source_state = getattr(state, source, None)
    if source_state:
        return item_id in source_state.seen_ids
    return False


def mark_approved(state: WatchState, url: str):
    """Mark an item as approved."""
    state.approved.append({
        "url": url,
        "approved_at": datetime.now().isoformat()
    })


def mark_rejected(state: WatchState, url: str):
    """Mark an item as rejected."""
    state.rejected.append({
        "url": url,
        "rejected_at": datetime.now().isoformat()
    })


def is_processed(state: WatchState, url: str) -> bool:
    """Check if an item has been approved or rejected."""
    for item in state.approved + state.rejected:
        if item.get("url") == url:
            return True
    return False
