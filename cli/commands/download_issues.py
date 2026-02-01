"""Download GitHub issues to text files."""

import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

console = Console()

# Target directory: parent of coding-scripts
TARGET_BASE = Path(__file__).parent.parent.parent.parent  # /home/shadeform


def download_issues():
    """Interactively select a repo and download its issues as txt files."""
    from github import Github
    from config import get_all_repos, get_github_token, GITHUB_OWNER

    token = get_github_token()
    if not token:
        console.print("[red]GITHUB_TOKEN environment variable not set.[/red]")
        console.print("Set it with: export GITHUB_TOKEN='your_token'")
        return

    g = Github(token)
    repos = get_all_repos()

    # Filter to repos with issues
    repos_with_issues = [r for r in repos if r.open_issues > 0]

    if not repos_with_issues:
        console.print("[yellow]No repos have open issues.[/yellow]")
        return

    # Display options
    console.print("\n[bold]Repos with open issues:[/bold]\n")
    for i, repo in enumerate(repos_with_issues, 1):
        console.print(f"  [cyan]{i}[/cyan]. {repo.name} ([red]{repo.open_issues} issues[/red])")

    console.print()

    # Get user selection
    choice = Prompt.ask(
        "Select a repo",
        choices=[str(i) for i in range(1, len(repos_with_issues) + 1)],
    )

    selected_repo = repos_with_issues[int(choice) - 1]
    console.print(f"\n[green]Selected:[/green] {selected_repo.name}")

    # Create output directory
    output_dir = TARGET_BASE / selected_repo.name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch and save issues
    with console.status(f"[bold green]Fetching issues from {selected_repo.name}..."):
        try:
            gh_repo = g.get_repo(f"{GITHUB_OWNER}/{selected_repo.name}")
            issues = list(gh_repo.get_issues(state="open"))

            # Filter out PRs
            issues = [i for i in issues if not i.pull_request]

            if not issues:
                console.print("[yellow]No open issues found (only PRs).[/yellow]")
                return

            for issue in issues:
                filename = f"issue_{issue.number}.txt"
                filepath = output_dir / filename

                # Build issue content
                content = []
                content.append(f"Issue #{issue.number}: {issue.title}")
                content.append("=" * 60)
                content.append(f"URL: {issue.html_url}")
                content.append(f"Author: {issue.user.login}")
                content.append(f"Created: {issue.created_at.strftime('%Y-%m-%d %H:%M')}")
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

            console.print(f"\n[green]Downloaded {len(issues)} issues to:[/green] {output_dir}")

        except Exception as e:
            console.print(f"[red]Error fetching issues: {e}[/red]")
