"""Download GitHub issues from all repos to text files."""

from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Target directory: /home/shadeform/issues/
TARGET_BASE = Path(__file__).parent.parent.parent.parent / "issues"


def download_all_issues(include_closed: bool = False):
    """Download issues from all repos as txt files."""
    from github import Github
    from config import get_all_repos, get_github_token, GITHUB_OWNER

    token = get_github_token()
    if not token:
        console.print("[red]GITHUB_TOKEN environment variable not set.[/red]")
        console.print("Set it with: export GITHUB_TOKEN='your_token'")
        return

    g = Github(token)
    repos = get_all_repos()

    state = "all" if include_closed else "open"

    # Create base output directory
    TARGET_BASE.mkdir(parents=True, exist_ok=True)

    total_issues = 0
    repos_with_issues = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing repos...", total=len(repos))

        for repo in repos:
            progress.update(task, description=f"Processing {repo.name}...")

            try:
                gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo.name}")
                issues = list(gh_repo.get_issues(state=state))

                # Filter out PRs
                issues = [i for i in issues if not i.pull_request]

                if not issues:
                    progress.advance(task)
                    continue

                # Create repo output directory
                output_dir = TARGET_BASE / repo.name
                output_dir.mkdir(parents=True, exist_ok=True)

                repos_with_issues += 1

                for issue in issues:
                    filename = f"issue_{issue.number}.txt"
                    filepath = output_dir / filename

                    # Build issue content
                    content = []
                    content.append(f"Issue #{issue.number}: {issue.title}")
                    content.append("=" * 60)
                    content.append(f"URL: {issue.html_url}")
                    content.append(f"Author: {issue.user.login}")
                    content.append(f"State: {issue.state}")
                    content.append(f"Created: {issue.created_at.strftime('%Y-%m-%d %H:%M')}")
                    if issue.closed_at:
                        content.append(f"Closed: {issue.closed_at.strftime('%Y-%m-%d %H:%M')}")
                    content.append(f"Labels: {', '.join([l.name for l in issue.labels]) or 'None'}")
                    content.append("")
                    content.append("--- Description ---")
                    content.append(issue.body or "(No description)")
                    content.append("")

                    # Fetch comments
                    comments = list(issue.get_comments())
                    if comments:
                        content.append(f"--- Comments ({len(comments)}) ---")
                        content.append("")
                        for comment in comments:
                            content.append(f"[{comment.user.login}] ({comment.created_at.strftime('%Y-%m-%d %H:%M')})")
                            content.append(comment.body or "(empty)")
                            content.append("-" * 40)
                            content.append("")

                    # Write file
                    with open(filepath, "w") as f:
                        f.write("\n".join(content))

                    total_issues += 1

            except Exception as e:
                console.print(f"[red]Error processing {repo.name}: {e}[/red]")

            progress.advance(task)

    console.print()
    console.print(f"[green]Downloaded {total_issues} issues from {repos_with_issues} repos to:[/green]")
    console.print(f"  {TARGET_BASE}/")
