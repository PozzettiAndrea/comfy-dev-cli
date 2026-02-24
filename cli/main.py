#!/usr/bin/env python3
"""
cds: CLI for ComfyUI development.

Subcommand groups:
    cds dev <cmd>       - Development workflow
    cds monitor <cmd>   - Monitoring and analysis
    cds clone <cmd>     - Clone and update repos
    cds oneshot <cmd>   - One-shot wrapper implementation
"""

import sys
import typer
from rich.console import Console

from config import require_github_token, setup_logging, get_logger, CT_ENVS_DIR

app = typer.Typer(
    name="cds",
    help="CLI for ComfyUI development",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main_callback(ctx: typer.Context):
    """Initialize logging for all commands."""
    command_name = ctx.invoked_subcommand or "cds"
    setup_logging(command_name)
    logger = get_logger()
    logger.info(f"Running: cds {' '.join(sys.argv[1:])}")


# =============================================================================
# DEV subcommand group
# =============================================================================

dev_app = typer.Typer(
    name="dev",
    help="Development workflow commands",
    no_args_is_help=True,
)
app.add_typer(dev_app, name="dev")


@dev_app.command("get")
def dev_get(
    config_name: str = typer.Argument(None, help="Config name (e.g., trellis2, sam3, unirig)"),
    reinstall: bool = typer.Option(False, "--reinstall", help="Delete existing folder and venv before fresh install"),
):
    """Set up a ComfyUI environment from a YAML config."""
    from commands.get import setup_comfyui, list_configs
    if config_name is None:
        list_configs()
    else:
        setup_comfyui(config_name, reinstall)


@dev_app.command("start")
def dev_start(
    repo_name: str = typer.Argument(..., help="Repository/environment name (e.g., trellis2, sam3)"),
    port: int = typer.Argument(None, help="Port to run ComfyUI on (default: 8188, auto-slides if not specified)"),
    cpu: bool = typer.Option(False, "--cpu", help="Run in CPU-only mode"),
):
    """Start ComfyUI in a virtual environment."""
    from commands.start import start_comfyui
    raise SystemExit(start_comfyui(repo_name, port, cpu))


@dev_app.command("test")
def dev_test(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., sam3dobjects, GeometryPack)"),
    gpu: bool = typer.Option(False, "--gpu", "-g", help="Enable GPU (sets COMFY_TEST_GPU=1)"),
    portable: bool = typer.Option(False, "--portable", "-P", help="Use windows-portable platform (Windows only)"),
    workflow: str = typer.Option(None, "--workflow", "-W", help="Run only this specific workflow"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing workspace directory"),
):
    """Run comfy-test locally."""
    from commands.test import run_test
    raise SystemExit(run_test(repo_name, gpu=gpu, portable=portable, workflow=workflow, force=force))


@dev_app.command("publish")
def dev_publish(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., depthanythingv3)"),
    push: bool = typer.Option(True, "--push/--no-push", "-p", help="Push to remote (default: push)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip uncommitted changes check"),
):
    """Publish test results to gh-pages branch for GitHub Pages."""
    from commands.publish import publish_results
    raise SystemExit(publish_results(repo_name, force, push))


@dev_app.command("show")
def dev_show(
    repo_name: str = typer.Argument(..., help="Package name (e.g., geometrypack)"),
    port: int = typer.Argument(8001, help="Port to serve on"),
    regenerate: bool = typer.Option(False, "--regenerate", "-r", help="Regenerate HTML report"),
):
    """View test results in browser (local preview of gh-pages)."""
    from commands.show import show_results
    raise SystemExit(show_results(repo_name, port, regenerate))


@dev_app.command("render")
def dev_render(
    workflow_file: str = typer.Argument(..., help="Path to workflow JSON file"),
    output: str = typer.Option(None, "-o", "--output", help="Output image path"),
):
    """Render a ComfyUI workflow JSON as an image."""
    from commands.render import render_command
    render_command(workflow_file, output)


@dev_app.command("status")
def dev_status():
    """Check for uncommitted changes in utils repos."""
    from commands.status import check_status
    check_status()


@dev_app.command("screenshot")
def dev_screenshot(
    port: int = typer.Argument(..., help="Port to screenshot (e.g., 8001)"),
    wait: int = typer.Option(3000, "--wait", "-w", help="Wait time in ms after page load"),
    output: str = typer.Option(None, "--output", "-o", help="Override output file path"),
):
    """Take a screenshot of a Brev-proxied page."""
    from commands.screenshot import take_screenshot
    from pathlib import Path
    output_path = Path(output) if output else None
    raise SystemExit(take_screenshot(port, wait_ms=wait, output_path=output_path))


@dev_app.command("activate")
def dev_activate(
    env_name: str = typer.Argument(None, help="Environment name to activate"),
):
    """Print activation command for a ct environment. Use with: eval $(cds dev activate <env>)"""
    import platform
    stderr_console = Console(stderr=True)

    if env_name is None:
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

    print(f"source {activate_script}")


# =============================================================================
# TOP-LEVEL ALIASES (hidden, for convenience)
# =============================================================================

@app.command("get", hidden=True)
def top_get(
    config_name: str = typer.Argument(None, help="Config name (e.g., trellis2, sam3, unirig)"),
    reinstall: bool = typer.Option(False, "--reinstall", help="Delete existing folder and venv before fresh install"),
):
    """Set up a ComfyUI environment from a YAML config."""
    dev_get(config_name, reinstall)


@app.command("start", hidden=True)
def top_start(
    repo_name: str = typer.Argument(..., help="Repository/environment name (e.g., trellis2, sam3)"),
    port: int = typer.Argument(None, help="Port to run ComfyUI on (default: 8188, auto-slides if not specified)"),
    cpu: bool = typer.Option(False, "--cpu", help="Run in CPU-only mode"),
):
    """Start ComfyUI in a virtual environment."""
    dev_start(repo_name, port, cpu)


@app.command("test", hidden=True)
def top_test(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., sam3dobjects, GeometryPack)"),
    gpu: bool = typer.Option(False, "--gpu", "-g", help="Enable GPU (sets COMFY_TEST_GPU=1)"),
    portable: bool = typer.Option(False, "--portable", "-P", help="Use windows-portable platform (Windows only)"),
    workflow: str = typer.Option(None, "--workflow", "-W", help="Run only this specific workflow"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing workspace directory"),
):
    """Run comfy-test locally."""
    dev_test(repo_name, gpu, portable, workflow, force)


@app.command("publish", hidden=True)
def top_publish(
    repo_name: str = typer.Argument(..., help="Repository name (e.g., depthanythingv3)"),
    push: bool = typer.Option(True, "--push/--no-push", "-p", help="Push to remote (default: push)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip uncommitted changes check"),
):
    """Publish test results to gh-pages branch for GitHub Pages."""
    dev_publish(repo_name, push, force)


@app.command("show", hidden=True)
def top_show(
    repo_name: str = typer.Argument(..., help="Package name (e.g., geometrypack)"),
    port: int = typer.Argument(8001, help="Port to serve on"),
    regenerate: bool = typer.Option(False, "--regenerate", "-r", help="Regenerate HTML report"),
):
    """View test results in browser (local preview of gh-pages)."""
    dev_show(repo_name, port, regenerate)


@app.command("render", hidden=True)
def top_render(
    workflow_file: str = typer.Argument(..., help="Path to workflow JSON file"),
    output: str = typer.Option(None, "-o", "--output", help="Output image path"),
):
    """Render a ComfyUI workflow JSON as an image."""
    dev_render(workflow_file, output)


@app.command("status", hidden=True)
def top_status():
    """Check for uncommitted changes in utils repos."""
    dev_status()


@app.command("screenshot", hidden=True)
def top_screenshot(
    port: int = typer.Argument(..., help="Port to screenshot (e.g., 8001)"),
    wait: int = typer.Option(3000, "--wait", "-w", help="Wait time in ms after page load"),
    output: str = typer.Option(None, "--output", "-o", help="Override output file path"),
):
    """Take a screenshot of a Brev-proxied page."""
    dev_screenshot(port, wait, output)


@app.command("activate", hidden=True)
def top_activate(
    env_name: str = typer.Argument(None, help="Environment name to activate"),
):
    """Print activation command for a ct environment. Use with: eval $(cds activate <env>)"""
    dev_activate(env_name)


# =============================================================================
# MONITOR subcommand group
# =============================================================================

monitor_app = typer.Typer(
    name="monitor",
    help="Monitoring and analysis commands",
    no_args_is_help=True,
)
app.add_typer(monitor_app, name="monitor")


@monitor_app.command("repos")
def monitor_repos():
    """List all managed repositories."""
    from rich.table import Table
    from config import get_all_repos

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


@monitor_app.command("teststatus")
def monitor_teststatus():
    """Show test results status from gh-pages across all repos."""
    from commands.teststatus import show_test_status
    raise SystemExit(show_test_status())


@monitor_app.command("runners")
def monitor_runners():
    """Show self-hosted runner status, active jobs, disk space, and GPU locks."""
    from commands.runners import monitor_runners as run_monitor
    run_monitor()


@monitor_app.command("dashboard")
def monitor_dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run dashboard on"),
):
    """Launch web dashboard."""
    require_github_token()
    from dashboard.app import run_dashboard
    run_dashboard(port)


@monitor_app.command("license")
def monitor_license(
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


@monitor_app.command("download-issues")
def monitor_download_issues():
    """Download issues from a repo as txt files."""
    require_github_token()
    from commands.download_issues import download_issues as dl_issues
    dl_issues()


@monitor_app.command("download-all-issues")
def monitor_download_all_issues(
    include_closed: bool = typer.Option(False, "--closed", "-c", help="Include closed issues"),
):
    """Download issues from ALL repos to ~/issues/{repo}/."""
    require_github_token()
    from commands.download_all_issues import download_all_issues as dl_all
    dl_all(include_closed)


@monitor_app.command("pages")
def monitor_pages(
    port: int = typer.Argument(8001, help="Port to serve the pages browser on"),
):
    """Browse all GitHub Pages sites in a local dashboard."""
    require_github_token()
    from commands.pages import serve_pages
    raise SystemExit(serve_pages(port))


@monitor_app.command("analyze-issues")
def monitor_analyze_issues(
    repo_name: str = typer.Option(None, "--repo", "-r", help="Analyze specific repo only"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-analyze even if already cached"),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=5, help="Parallel Claude instances (1-5)"),
):
    """Analyze GitHub issues using Claude Code to find probable causes."""
    require_github_token()
    from commands.analyze_issues import analyze_issues as run_analysis
    run_analysis(repo_name, force, workers)


# =============================================================================
# CLONE subcommand group
# =============================================================================

clone_app = typer.Typer(
    name="clone",
    help="Clone and update repos",
    no_args_is_help=True,
)
app.add_typer(clone_app, name="clone")


@clone_app.command("nodes")
def clone_nodes(
    threshold: int = typer.Option(..., "--threshold", "-t", help="Minimum star count to clone"),
):
    """Clone all ComfyUI nodes to ~/all_repos/."""
    require_github_token()
    from commands.clone_all import clone_all_repos
    clone_all_repos(pull_existing=False, threshold=threshold)


@clone_app.command("utils")
def clone_utils():
    """Clone all comfy-* utility repos to ~/utils/."""
    require_github_token()
    from commands.clone_utils import clone_utils_repos
    clone_utils_repos(pull_existing=False)


@clone_app.command("pull")
def clone_pull():
    """Pull latest changes for all cloned nodes in ~/all_repos/."""
    require_github_token()
    from commands.clone_all import pull_all_repos
    pull_all_repos()


# =============================================================================
# ONESHOT subcommand group (from oneshot/cli.py)
# =============================================================================

from oneshot.cli import app as oneshot_app
app.add_typer(oneshot_app, name="oneshot")


# =============================================================================
# PRIVATE EXTENSIONS (loaded from ~/coding-scripts/private/cli if exists)
# =============================================================================

try:
    from pathlib import Path
    private_cli = Path.home() / "coding-scripts" / "private" / "cli"
    if private_cli.exists() and (private_cli / "extensions.py").exists():
        import sys
        sys.path.insert(0, str(private_cli))
        from extensions import register_private_commands
        register_private_commands(app, typer, console, require_github_token)
except Exception as e:
    import os
    if os.environ.get("CDS_DEBUG"):
        print(f"Extension load error: {e}")


if __name__ == "__main__":
    app()
