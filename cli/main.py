#!/usr/bin/env python3
"""
ct: Unified CLI for ComfyUI development tools.

Subcommand groups:
    ct oneshot <cmd>    - One-shot wrapper implementation workflow
    ct index <cmd>      - ComfyUI 3D nodes index management
    ct watch <cmd>      - Monitor sources for new 3D AI projects
    ct projects <cmd>   - Google Sheets project tracking

Top-level commands:
    ct repos            - List all managed repositories
    ct get <config>     - Set up ComfyUI environment from config
    ct activate <env>   - Print activation command (use with eval)
    ct test <repo>      - Run comfy-test locally or in VM
    ct show <repo>      - View test results in browser
    ct publish <repo>   - Publish test results to gh-pages
    ct dashboard        - Launch web dashboard
    ct license          - Audit licenses across repos
    ct commits          - Check for work-hours commits
    ct analyze-issues   - Analyze issues using Claude
    ct clone-nodes      - Clone all ComfyUI nodes
    ct pull-nodes       - Pull latest changes for all ComfyUI nodes
    ct clone-utils      - Clone all comfy-* utility repos
"""

import sys
import typer
from rich.console import Console
from rich.table import Table

from config import get_all_repos, GITHUB_OWNER, require_github_token, setup_logging, get_logger, CT_ENVS_DIR

app = typer.Typer(
    name="ct",
    help="Unified CLI for ComfyUI development tools",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main_callback(ctx: typer.Context):
    """Initialize logging for all ct commands."""
    # Get the command name from the invoked subcommand
    command_name = ctx.invoked_subcommand or "ct"
    setup_logging(command_name)
    logger = get_logger()
    logger.info(f"Running: ct {' '.join(sys.argv[1:])}")


# =============================================================================
# Top-level commands
# =============================================================================

@app.command()
def repos():
    """List all managed repositories."""
    all_repos = get_all_repos()

    table = Table(title=f"Managed Repos ({len(all_repos)} total)")
    table.add_column("Name", style="cyan")
    table.add_column("Stars", justify="right", style="yellow")
    table.add_column("Issues", justify="right", style="red")
    table.add_column("PRs", justify="right", style="magenta")
    table.add_column("Forks", justify="right")

    for repo in sorted(all_repos, key=lambda r: r.stars, reverse=True):
        table.add_row(
            repo.name,
            str(repo.stars),
            str(repo.open_issues),
            str(repo.open_prs),
            str(repo.forks),
        )

    console.print(table)


@app.command()
def status():
    """Check for uncommitted changes in utils repos."""
    from commands.status import check_status
    check_status()


@app.command()
def get(
    config_name: str = typer.Argument(None, help="Config name (e.g., trellis2, sam3, unirig)"),
    reinstall: bool = typer.Option(False, "--reinstall", help="Delete existing folder and venv before fresh install"),
):
    """Set up a ComfyUI environment from a YAML config."""
    from commands.get import setup_comfyui, list_configs
    if config_name is None:
        list_configs()
    else:
        setup_comfyui(config_name, reinstall)


@app.command()
def activate(
    env_name: str = typer.Argument(None, help="Environment name to activate"),
):
    """Print activation command for a ct environment. Use with: eval $(ct activate <env>)"""
    import platform
    from rich.console import Console
    stderr_console = Console(stderr=True)

    if env_name is None:
        # List available environments (to stderr so it doesn't break eval)
        if CT_ENVS_DIR.exists():
            envs = sorted([d.name for d in CT_ENVS_DIR.iterdir() if d.is_dir()])
            if envs:
                stderr_console.print("[bold]Available environments:[/bold]")
                for env in envs:
                    stderr_console.print(f"  [cyan]{env}[/cyan]")
            else:
                stderr_console.print("[yellow]No environments found.[/yellow]")
        else:
            stderr_console.print("[yellow]No environments directory found.[/yellow]")
        return

    env_path = CT_ENVS_DIR / env_name
    if not env_path.exists():
        stderr_console.print(f"[red]Environment not found: {env_name}[/red]")
        raise SystemExit(1)

    if platform.system() == "Windows":
        activate_script = env_path / "Scripts" / "activate.bat"
    else:
        activate_script = env_path / "bin" / "activate"

    # Print only the source command to stdout (for eval)
    print(f"source {activate_script}")


@app.command()
def license(
    repo_name: str = typer.Option(None, "--repo", "-r", help="Filter by repo name"),
    deep: bool = typer.Option(False, "--deep", "-d", help="Deep AI-powered license analysis"),
):
    """Audit licenses across all repos."""
    require_github_token()
    from commands.license import audit_licenses, deep_audit_licenses
    if deep:
        deep_audit_licenses(repo_name)
    else:
        audit_licenses(repo_name)


@app.command()
def commits(
    repo_name: str = typer.Option(None, "--repo", "-r", help="Filter by repo name"),
    days: int = typer.Option(90, "--days", "-d", help="Look back N days"),
):
    """Check for work-hours commits (9-5 weekdays)."""
    require_github_token()
    from commands.commits import check_commits
    check_commits(repo_name, days)


@app.command()
def dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run dashboard on"),
):
    """Launch web dashboard."""
    require_github_token()
    from dashboard.app import run_dashboard
    run_dashboard(port)


@app.command()
def download_issues():
    """Download issues from a repo as txt files."""
    require_github_token()
    from commands.download_issues import download_issues as dl_issues
    dl_issues()


@app.command()
def download_all_issues(
    include_closed: bool = typer.Option(False, "--closed", "-c", help="Include closed issues"),
):
    """Download issues from ALL repos to ~/issues/{repo}/."""
    require_github_token()
    from commands.download_all_issues import download_all_issues as dl_all
    dl_all(include_closed)


@app.command("clone-nodes")
def clone_nodes(
    pull: bool = typer.Option(False, "--pull", "-p", help="Pull latest changes for existing repos"),
):
    """Clone all ComfyUI nodes to ~/all_repos/."""
    require_github_token()
    from commands.clone_all import clone_all_repos
    clone_all_repos(pull)


@app.command("pull-nodes")
def pull_nodes():
    """Pull latest changes for all ComfyUI nodes in ~/all_repos/."""
    require_github_token()
    from commands.clone_all import pull_all_repos
    pull_all_repos()


@app.command("clone-utils")
def clone_utils(
    pull: bool = typer.Option(False, "--pull", "-p", help="Pull latest changes for existing repos"),
):
    """Clone all comfy-* utility repos to ~/utils/."""
    require_github_token()
    from commands.clone_utils import clone_utils_repos
    clone_utils_repos(pull)


@app.command("analyze-issues")
def analyze_issues(
    repo_name: str = typer.Option(None, "--repo", "-r", help="Analyze specific repo only"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-analyze even if already cached"),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=5, help="Parallel Claude instances (1-5)"),
):
    """Analyze GitHub issues using Claude Code to find probable causes."""
    require_github_token()
    from commands.analyze_issues import analyze_issues as run_analysis
    run_analysis(repo_name, force, workers)


@app.command()
def render(
    workflow_file: str = typer.Argument(..., help="Path to workflow JSON file"),
    output: str = typer.Option(None, "-o", "--output", help="Output image path"),
):
    """Render a ComfyUI workflow JSON as an image."""
    from commands.render import render_command
    render_command(workflow_file, output)


@app.command()
def start(
    repo_name: str = typer.Argument(..., help="Repository/environment name (e.g., trellis2, sam3)"),
    port: int = typer.Argument(8188, help="Port to run ComfyUI on"),
    cpu: bool = typer.Option(False, "--cpu", help="Run in CPU-only mode"),
):
    """Start ComfyUI in a virtual environment."""
    from commands.start import start_comfyui
    raise SystemExit(start_comfyui(repo_name, port, cpu))


# =============================================================================
# Oneshot subcommand group
# =============================================================================

from oneshot.cli import app as oneshot_app
app.add_typer(oneshot_app, name="oneshot")


# =============================================================================
# 3D Index subcommand group
# =============================================================================

_index_app = typer.Typer(
    name="index",
    help="Manage ComfyUI 3D nodes index",
    no_args_is_help=True,
)
app.add_typer(_index_app, name="index")


@_index_app.command("fetch")
def index_fetch(
    skip_readmes: bool = typer.Option(False, "--skip-readmes", help="Skip README fetching (faster)"),
    workers: int = typer.Option(None, "--workers", "-w", help="Override worker count"),
):
    """Fetch all ComfyUI nodes from Manager and Registry."""
    from index.fetch import fetch_all
    fetch_all(skip_readmes=skip_readmes, workers=workers)


@_index_app.command("classify")
def index_classify(
    input_file: str = typer.Option(None, "--input", "-i", help="Input CSV file"),
    top_n: int = typer.Option(None, "--top", "-n", help="Classify only top N by stars"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-classify even if in skip list"),
    workers: int = typer.Option(None, "--workers", "-w", help="Override worker count"),
):
    """Classify nodes for 3D relevance using DeepSeek."""
    from index.classify import classify_nodes
    classify_nodes(input_file=input_file, top_n=top_n, force=force, workers=workers)


@_index_app.command("generate")
def index_generate(
    input_file: str = typer.Option(None, "--input", "-i", help="Input CSV file"),
    skip_clone: bool = typer.Option(False, "--skip-clone", help="Skip repo cloning for node extraction"),
    skip_media: bool = typer.Option(False, "--skip-media", help="Skip media fetching"),
):
    """Generate HTML index from classified 3D nodes."""
    from index.generate import generate_index
    generate_index(input_file=input_file, skip_clone=skip_clone, skip_media=skip_media)


@_index_app.command("all")
def index_all(
    top_n: int = typer.Option(None, "--top", "-n", help="Classify only top N by stars"),
):
    """Run full pipeline: fetch -> classify -> generate."""
    from index.fetch import fetch_all
    from index.classify import classify_nodes
    from index.generate import generate_index

    console.print("[bold cyan]Step 1/3: Fetching nodes...[/bold cyan]")
    fetch_all()

    console.print("\n[bold cyan]Step 2/3: Classifying nodes...[/bold cyan]")
    classify_nodes(top_n=top_n)

    console.print("\n[bold cyan]Step 3/3: Generating HTML...[/bold cyan]")
    generate_index()

    console.print("\n[green bold]Pipeline complete![/green bold]")


# =============================================================================
# 3D Watch subcommand group
# =============================================================================

_watch_app = typer.Typer(
    name="watch",
    help="Monitor sources for new 3D AI projects",
    no_args_is_help=True,
)
app.add_typer(_watch_app, name="watch")


@_watch_app.command("run")
def watch_run(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show items but don't send to Discord"),
    sources: str = typer.Option(None, "--sources", "-s", help="Comma-separated sources: github,twitter,reddit"),
    days: int = typer.Option(30, "--days", "-d", help="Look back this many days"),
):
    """Check sources for new 3D AI projects and send to Discord for review."""
    from watch.main import run_watch
    run_watch(dry_run=dry_run, sources=sources, days=days)


@_watch_app.command("status")
def watch_status():
    """Show current watcher status."""
    from watch.main import show_status
    show_status()


@_watch_app.command("reset")
def watch_reset(
    source: str = typer.Option(None, "--source", "-s", help="Reset specific source (github/twitter/reddit)"),
):
    """Reset watcher state (clear seen items)."""
    from watch.main import reset_state
    reset_state(source)


# =============================================================================
# Projects subcommand group (Google Sheets tracking)
# =============================================================================

_projects_app = typer.Typer(
    name="projects",
    help="Manage 3D AI project tracking spreadsheet",
    no_args_is_help=True,
)
app.add_typer(_projects_app, name="projects")


@_projects_app.command("list")
def projects_list(
    status: str = typer.Option(None, "--status", "-s", help="Filter by status (Done/NYI/In development)"),
    org: str = typer.Option(None, "--org", "-o", help="Filter by organisation"),
):
    """List all tracked projects."""
    from projects.commands import list_projects
    list_projects(status_filter=status, org_filter=org)


@_projects_app.command("show")
def projects_show(
    name: str = typer.Argument(..., help="Project name"),
):
    """Show details for a specific project."""
    from projects.commands import show_project
    show_project(name)


@_projects_app.command("status")
def projects_status(
    name: str = typer.Argument(..., help="Project name"),
    new_status: str = typer.Argument(..., help="New status (Done/NYI/In development)"),
):
    """Update a project's status."""
    from projects.commands import update_status
    update_status(name, new_status)


@_projects_app.command("add")
def projects_add(
    name: str = typer.Argument(..., help="Project name"),
    org: str = typer.Argument(..., help="Organisation"),
    github: str = typer.Argument(..., help="GitHub URL"),
    desc: str = typer.Option("", "--desc", "-d", help="Description"),
    priority: str = typer.Option("", "--priority", "-p", help="Priority"),
):
    """Add a new project to track."""
    from projects.commands import add_project
    add_project(name, org, github, desc, priority)


# =============================================================================
# Test command - run comfy-test locally or in Windows VM
# =============================================================================

@app.command()
def test(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., sam3dobjects, GeometryPack)"),
    gpu: bool = typer.Option(False, "--gpu", "-g", help="Enable GPU (sets COMFY_TEST_GPU=1)"),
    portable: bool = typer.Option(False, "--portable", "-P", help="Use windows-portable platform (Windows only)"),
    direct: bool = typer.Option(False, "--direct", "-d", help="Run directly without Docker (auto-detected on Windows if Docker unavailable)"),
    workflow: str = typer.Option(None, "--workflow", "-W", help="Run only this specific workflow (e.g., fix_normals.json)"),
):
    """Run comfy-test locally. Auto-detects OS and Docker availability."""
    from commands.test import run_test
    raise SystemExit(run_test(repo_name, gpu=gpu, portable=portable, direct=direct, workflow=workflow))


@app.command()
def show(
    repo_name: str = typer.Argument(..., help="Package name (e.g., geometrypack)"),
    port: int = typer.Argument(8001, help="Port to serve on"),
    regenerate: bool = typer.Option(False, "--regenerate", "-r", help="Regenerate HTML report"),
):
    """View test results in browser (local preview of gh-pages)."""
    from commands.show import show_results
    raise SystemExit(show_results(repo_name, port, regenerate))


@app.command()
def publish(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., depthanythingv3)"),
    push: bool = typer.Option(False, "--push", "-p", help="Push to remote (default: local only)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip uncommitted changes check"),
):
    """Publish test results to gh-pages branch for GitHub Pages."""
    from commands.publish import publish_results
    raise SystemExit(publish_results(repo_name, force, push))


if __name__ == "__main__":
    app()
