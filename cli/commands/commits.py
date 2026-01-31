"""Check for work-hours commits (9-5 weekdays)."""

from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

console = Console()


def check_commits(repo_name: str | None, days: int):
    """Check for commits made during work hours (9 AM - 5 PM weekdays)."""
    from github import Github
    from config import get_all_repos, get_github_token, GITHUB_OWNER

    token = get_github_token()
    if not token:
        console.print("[red]GITHUB_TOKEN environment variable not set.[/red]")
        return

    g = Github(token)
    repos = get_all_repos()

    if repo_name:
        repos = [r for r in repos if r.name == repo_name]

    since = datetime.now() - timedelta(days=days)

    table = Table(title=f"Work-Hours Commits (last {days} days)")
    table.add_column("Repo", style="cyan")
    table.add_column("Total Commits", justify="right")
    table.add_column("Work Hours", justify="right", style="red")
    table.add_column("Percentage", justify="right")
    table.add_column("Status", style="bold")

    from tqdm import tqdm

    results = []

    for repo in tqdm(repos, desc="Analyzing commits"):
        try:
            gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo.name}")
            commits = gh_repo.get_commits(since=since)

            total = 0
            work_hours = 0
            work_hours_commits = []

            for commit in commits:
                total += 1
                date = commit.commit.author.date
                # Check if weekday (0-4) and between 9-17
                if date.weekday() < 5 and 9 <= date.hour < 17:
                    work_hours += 1
                    work_hours_commits.append({
                        "date": date,
                        "message": commit.commit.message.split("\n")[0][:50],
                    })

            if total > 0:
                pct = (work_hours / total) * 100
                if pct > 50:
                    status = "High Risk"
                    status_style = "red"
                elif pct > 20:
                    status = "Warning"
                    status_style = "yellow"
                else:
                    status = "OK"
                    status_style = "green"
            else:
                pct = 0
                status = "No commits"
                status_style = "dim"

            results.append({
                "repo": repo.name,
                "total": total,
                "work_hours": work_hours,
                "pct": pct,
                "status": status,
                "status_style": status_style,
                "commits": work_hours_commits,
            })

        except Exception as e:
            console.print(f"[dim]Skipping {repo.name}: {e}[/dim]")

    # Sort by percentage descending
    results.sort(key=lambda x: x["pct"], reverse=True)

    for r in results:
        table.add_row(
            r["repo"],
            str(r["total"]),
            str(r["work_hours"]),
            f"{r['pct']:.1f}%",
            f"[{r['status_style']}]{r['status']}[/{r['status_style']}]",
        )

    console.print(table)

    # Show problematic commits
    problem_repos = [r for r in results if r["pct"] > 20]
    if problem_repos:
        console.print("\n[bold red]Problematic Commits (9 AM - 5 PM weekdays):[/bold red]")
        for r in problem_repos[:5]:
            console.print(f"\n[cyan]{r['repo']}[/cyan]:")
            for c in r["commits"][:5]:
                console.print(f"  {c['date'].strftime('%Y-%m-%d %H:%M')} - {c['message']}")

    total_work = sum(r["work_hours"] for r in results)
    total_all = sum(r["total"] for r in results)
    if total_all > 0:
        console.print(f"\n[bold]Overall: {total_work}/{total_all} commits ({total_work/total_all*100:.1f}%) during work hours[/bold]")
