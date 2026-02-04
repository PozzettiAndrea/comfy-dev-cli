"""Show test results in browser.

This module implements the `ct show` command which serves test results
locally, providing an exact preview of what appears on gh-pages.

Structure matches CI gh-pages:
  logs/RepoName-HHMM/
    index.html              <- branch switcher
    {branch}/
      index.html            <- platform tabs
      {platform}/
        index.html          <- test report
        results.json
"""

import http.server
import os
import platform
import socketserver
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# Platform IDs that ct test can generate
PLATFORM_IDS = [
    'linux-cpu', 'linux-gpu',
    'windows-cpu', 'windows-gpu',
    'windows-portable-cpu', 'windows-portable-gpu',
    'macos-cpu', 'macos-gpu',
]

# Import report generators from comfy-test
try:
    sys.path.insert(0, str(Path.home() / "utils" / "comfy-test" / "src"))
    from comfy_test.reporting.html_report import generate_html_report, generate_root_index, generate_branch_root_index
    HAS_REPORT_GENERATOR = True
except ImportError:
    HAS_REPORT_GENERATOR = False


def _fix_permissions_if_needed(folder: Path) -> None:
    """Fix file permissions if Docker created files as root."""
    import subprocess
    import getpass

    uid = os.getuid()
    try:
        for f in folder.rglob("*"):
            if f.exists() and f.stat().st_uid != uid:
                console.print("[dim]Fixing file permissions...[/dim]")
                user = getpass.getuser()
                subprocess.run(["sudo", "chown", "-R", f"{user}:{user}", str(folder)], check=True)
                return
    except Exception:
        pass


def find_latest_log(repo_name: str, timestamp: str = None) -> Optional[Path]:
    """Find a test run folder for a repo."""
    if platform.system() == "Windows":
        logs_dir = Path.home() / "Desktop" / "logs"
    else:
        logs_dir = Path.home() / "logs"

    if not logs_dir.exists():
        return None

    repo_lower = repo_name.lower().replace("-", "").replace("_", "")
    candidates = []

    for folder in logs_dir.iterdir():
        if not folder.is_dir():
            continue

        parts = folder.name.rsplit("-", 1)
        if len(parts) < 2:
            continue

        base_name, folder_timestamp = parts
        base_lower = base_name.lower().replace("-", "").replace("_", "")

        if repo_lower == base_lower:
            if timestamp:
                if folder_timestamp == timestamp:
                    return folder
            else:
                candidates.append(folder)

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def find_branches(log_folder: Path) -> list[Path]:
    """Find branch folders (directories containing platform subdirs)."""
    branches = []
    for subdir in log_folder.iterdir():
        if not subdir.is_dir() or subdir.name.startswith('.'):
            continue
        # A branch folder contains at least one platform subdir
        for platform_id in PLATFORM_IDS:
            if (subdir / platform_id).exists():
                branches.append(subdir)
                break
    return branches


def show_results(repo_name: str, port: int = 8001, regenerate: bool = False, timestamp: str = None) -> int:
    """Find test run and serve the generated HTML report (matches gh-pages structure)."""
    if not HAS_REPORT_GENERATOR:
        console.print("[red]comfy-test not found. Install it first.[/red]")
        return 1

    # Find log folder
    log_folder = find_latest_log(repo_name, timestamp)
    if log_folder is None:
        console.print(f"[red]No test runs found for '{repo_name}'[/red]")
        logs_path = "~/Desktop/logs/" if platform.system() == "Windows" else "~/logs/"
        console.print(f"[dim]Searched in: {logs_path}[/dim]")
        return 1

    console.print(f"[dim]Found: {log_folder}[/dim]")
    _fix_permissions_if_needed(log_folder)

    # Find branch folders
    branches = find_branches(log_folder)
    if not branches:
        console.print(f"[red]No branch folders found in {log_folder}[/red]")
        console.print(f"[dim]Expected structure: {log_folder}/{{branch}}/{{platform}}/results.json[/dim]")
        return 1

    # Generate reports for each branch
    for branch_folder in branches:
        console.print(f"[dim]Branch: {branch_folder.name}[/dim]")

        # Generate platform reports
        for platform_id in PLATFORM_IDS:
            platform_dir = branch_folder / platform_id
            results_file = platform_dir / "results.json"
            if results_file.exists():
                console.print(f"[dim]  Generating {platform_id} report...[/dim]")
                try:
                    generate_html_report(platform_dir, repo_name, current_platform=platform_id)
                except Exception as e:
                    console.print(f"[yellow]  Warning: {e}[/yellow]")

        # Generate branch index (platform tabs)
        console.print(f"[dim]  Generating branch index...[/dim]")
        generate_root_index(branch_folder, repo_name)

    # Generate root index (branch switcher)
    console.print("[dim]Generating root index (branch switcher)...[/dim]")
    generate_branch_root_index(log_folder, repo_name)

    # Serve from log_folder
    os.chdir(log_folder)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    # Try ports
    actual_port = port
    httpd = None
    for attempt in range(10):
        try:
            httpd = ReusableTCPServer(("0.0.0.0", actual_port), QuietHandler)
            break
        except OSError as e:
            if "Address already in use" in str(e) and attempt < 9:
                actual_port += 1
            else:
                console.print(f"[red]Server error: {e}[/red]")
                return 1

    try:
        if actual_port != port:
            console.print(f"[yellow]Port {port} busy, using {actual_port}[/yellow]")
        console.print(f"[green]Serving at http://0.0.0.0:{actual_port}[/green]")
        console.print(f"[dim]Press Ctrl+C to stop[/dim]")
        webbrowser.open(f"http://localhost:{actual_port}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped[/dim]")
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()

    return 0
