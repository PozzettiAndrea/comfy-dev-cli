"""README caching with hash-based change detection."""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from .github import extract_github_info, fetch_readme


class ReadmeCache:
    """Cache for README files to avoid re-fetching."""

    def __init__(self, cache_dir, max_age_days=7):
        self.cache_dir = Path(cache_dir)
        self.index_file = self.cache_dir / "index.json"
        self.max_age_days = max_age_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    self.index = json.load(f)
            except Exception:
                self.index = {}
        else:
            self.index = {}

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def _get_key(self, github_url):
        owner, repo = extract_github_info(github_url)
        if owner and repo:
            return f"{owner}_{repo}"
        return None

    def get(self, github_url, force_refresh=False):
        """Get README content, fetching if needed."""
        key = self._get_key(github_url)
        if not key:
            return ""

        entry = self.index.get(key)

        # Check if we need to fetch
        needs_fetch = (
            force_refresh or
            entry is None or
            self._is_stale(entry)
        )

        if needs_fetch:
            owner, repo = extract_github_info(github_url)
            content, branch = fetch_readme(owner, repo)
            self._store(key, content, github_url)
            return content

        # Read from cache
        cache_file = self.cache_dir / f"{key}.md"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8", errors="replace")
        return ""

    def _is_stale(self, entry):
        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
            return datetime.now() - fetched > timedelta(days=self.max_age_days)
        except Exception:
            return True

    def _store(self, key, content, github_url):
        cache_file = self.cache_dir / f"{key}.md"
        cache_file.write_text(content, encoding="utf-8")

        self.index[key] = {
            "github_url": github_url,
            "hash": hashlib.md5(content.encode()).hexdigest(),
            "fetched_at": datetime.now().isoformat(),
            "size": len(content),
        }
        self._save_index()

    def get_stats(self):
        """Get cache statistics."""
        total = len(self.index)
        stale = sum(1 for entry in self.index.values() if self._is_stale(entry))
        total_size = sum(entry.get("size", 0) for entry in self.index.values())
        return {
            "total_cached": total,
            "stale": stale,
            "fresh": total - stale,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
