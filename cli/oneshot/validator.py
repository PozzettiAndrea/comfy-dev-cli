"""Main repo validator class and report dataclass."""

import json
import os
from dataclasses import dataclass, field, asdict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .patterns import parse_github_url
from .extractors import (
    extract_huggingface_links,
    search_huggingface_api,
    extract_paper_links,
    extract_website_links,
    fetch_github_metadata,
    fetch_readme,
)


console = Console()


@dataclass
class ValidationReport:
    """Report containing validation results for a repo."""

    # Input
    github_url: str = ""
    owner: str = ""
    repo: str = ""

    # GitHub metadata
    github_meta: dict = field(default_factory=dict)

    # Detected resources
    huggingface_readme: list = field(default_factory=list)  # From README parsing
    huggingface_api: list = field(default_factory=list)     # From HF API search
    papers: list = field(default_factory=list)
    website: str = None

    # Validation result
    score: int = 0
    ready: bool = False
    errors: list = field(default_factory=list)

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return asdict(self)

    def to_json(self):
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @property
    def all_huggingface(self):
        """Combined HF links from all sources."""
        seen = set()
        result = []
        for url in self.huggingface_readme:
            if url not in seen:
                seen.add(url)
                result.append(url)
        for item in self.huggingface_api:
            url = item.get("url", "") if isinstance(item, dict) else item
            if url not in seen:
                seen.add(url)
                result.append(url)
        return result


class RepoValidator:
    """Validates if a repo has prerequisites for ComfyUI wrapper implementation."""

    def __init__(self, github_token=None):
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

    def validate(self, github_url_or_shorthand):
        """
        Validate a GitHub repo.

        Args:
            github_url_or_shorthand: Full GitHub URL or owner/repo shorthand

        Returns:
            ValidationReport with all findings
        """
        report = ValidationReport()

        # Parse GitHub URL
        owner, repo = parse_github_url(github_url_or_shorthand)
        if not owner or not repo:
            report.errors.append(f"Invalid GitHub URL or shorthand: {github_url_or_shorthand}")
            return report

        report.owner = owner
        report.repo = repo
        report.github_url = f"https://github.com/{owner}/{repo}"

        # Fetch GitHub metadata
        meta = fetch_github_metadata(owner, repo, self.github_token)
        report.github_meta = meta

        if "error" in meta:
            report.errors.append(f"GitHub API error: {meta['error']}")
            return report

        # Fetch README
        readme = fetch_readme(owner, repo, self.github_token, meta.get("default_branch", "main"))
        description = meta.get("description", "")

        # Combine text for searching
        combined_text = f"{description}\n\n{readme or ''}"

        # Extract HuggingFace links from README
        report.huggingface_readme = extract_huggingface_links(combined_text, repo, owner)

        # Search HuggingFace API
        report.huggingface_api = search_huggingface_api(repo, owner)

        # Extract paper links
        report.papers = extract_paper_links(combined_text)

        # Extract website
        report.website = extract_website_links(combined_text, repo)

        # Calculate score
        score = 0
        if not meta.get("error"):
            score += 1  # GitHub accessible
        if report.all_huggingface:
            score += 1  # HuggingFace found
        if report.papers:
            score += 1  # Papers found
        if report.website:
            score += 1  # Website found

        report.score = score
        report.ready = score >= 2  # GitHub + at least HF

        return report

    def print_report(self, report):
        """Print formatted validation report to console."""
        if report.errors and not report.github_meta:
            console.print(f"[red]Validation failed: {report.errors[0]}[/red]")
            return

        # Header
        title = f"{report.repo} - Validation Report"
        console.print()
        console.print(f"[bold]{title}[/bold]")
        console.print("─" * len(title))

        # GitHub
        meta = report.github_meta
        if "error" not in meta:
            stars = meta.get("stars", 0)
            stars_fmt = f"{stars/1000:.1f}k" if stars >= 1000 else str(stars)
            lang = meta.get("language", "Unknown")
            license_ = meta.get("license") or "None"

            console.print(f"[green]✓[/green] [bold]GitHub:[/bold] {report.github_url}")
            console.print(f"  └─ Stars: {stars_fmt} | Language: {lang} | License: {license_}")
        else:
            console.print(f"[red]✗[/red] [bold]GitHub:[/bold] {meta.get('error')}")

        # HuggingFace
        hf_all = report.all_huggingface
        if hf_all:
            console.print(f"[green]✓[/green] [bold]HuggingFace:[/bold]")
            for url in hf_all[:5]:  # Show max 5
                console.print(f"  └─ {url}")
            if len(hf_all) > 5:
                console.print(f"  └─ ... and {len(hf_all) - 5} more")
        else:
            console.print(f"[red]✗[/red] [bold]HuggingFace:[/bold] Not found")

        # Papers
        if report.papers:
            console.print(f"[green]✓[/green] [bold]Paper:[/bold]")
            for url in report.papers[:3]:  # Show max 3
                console.print(f"  └─ {url}")
            if len(report.papers) > 3:
                console.print(f"  └─ ... and {len(report.papers) - 3} more")
        else:
            console.print(f"[red]✗[/red] [bold]Paper:[/bold] Not found")

        # Website
        if report.website:
            console.print(f"[green]✓[/green] [bold]Website:[/bold] {report.website}")
        else:
            console.print(f"[yellow]○[/yellow] [bold]Website:[/bold] Not found")

        # Score
        console.print()
        score_color = "green" if report.score >= 3 else "yellow" if report.score >= 2 else "red"

        if report.score == 4:
            verdict = "Ideal candidate"
        elif report.score == 3:
            verdict = "Good candidate"
        elif report.score == 2:
            verdict = "Minimal viable - has GitHub + HF"
        elif report.score == 1:
            verdict = "Missing key info, manual research needed"
        else:
            verdict = "Not accessible"

        console.print(f"[{score_color}]Score: {report.score}/4 - {verdict}[/{score_color}]")

        if report.ready:
            console.print("[green]Ready for one-shot implementation[/green]")
        else:
            console.print("[yellow]May need manual research for missing resources[/yellow]")

        console.print()
