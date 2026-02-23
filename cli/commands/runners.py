"""Monitor self-hosted GitHub runners on ROADRUNNER."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from config import GITHUB_OWNER

console = Console()

# Repos with self-hosted runners
RUNNER_REPOS = [
    "ComfyUI-SAM3",
    "ComfyUI-SAM3DBody",
    "ComfyUI-SAM3DObjects",
    "ComfyUI-Hunyuan3D-Part",
    "ComfyUI-DepthAnythingV3",
    "ComfyUI-GeometryPack",
    "ComfyUI-MotionCapture",
    "ComfyUI-Sharp",
    "ComfyUI-TRELLIS2",
    "ComfyUI-UniRig",
]

def _get_roadrunner_creds() -> tuple[str, str, str]:
    """Get ROADRUNNER SSH credentials from environment."""
    import os
    host = os.environ.get("ROADRUNNER_HOST", "")
    user = os.environ.get("ROADRUNNER_USER", "")
    password = os.environ.get("ROADRUNNER_PASS", "")
    if not all([host, user, password]):
        console.print("[red]ROADRUNNER_HOST, ROADRUNNER_USER, ROADRUNNER_PASS must be set in ~/coding-scripts/private/.env[/red]")
        raise SystemExit(1)
    return host, user, password


def _ssh_cmd(cmd: str, timeout: int = 10) -> str:
    """Run a command on ROADRUNNER via SSH."""
    host, user, password = _get_roadrunner_creds()
    try:
        result = subprocess.run(
            ["sshpass", "-p", password, "ssh",
             "-o", "StrictHostKeyChecking=no",
             "-o", f"ConnectTimeout={timeout}",
             f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def _gh_api(endpoint: str) -> dict | list | None:
    """Call GitHub API via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def _get_repo_runs(repo: str) -> tuple[str, list]:
    """Get in-progress and queued runs for a repo."""
    runs = []
    for status in ["in_progress", "queued"]:
        data = _gh_api(f"repos/{GITHUB_OWNER}/{repo}/actions/runs?status={status}&per_page=5")
        if data and "workflow_runs" in data:
            for run in data["workflow_runs"]:
                runs.append({
                    "repo": repo,
                    "status": run["status"],
                    "name": run["name"],
                    "branch": run.get("head_branch", "?"),
                    "run_id": run["id"],
                    "url": run["html_url"],
                    "started": run.get("run_started_at", "")[:19].replace("T", " "),
                })
    return repo, runs


def monitor_runners():
    """Show runner status, active jobs, disk space, and locks."""

    # --- Active/queued runs across all repos (parallel) ---
    console.print("[bold blue]Fetching runner activity...[/bold blue]")
    all_runs = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_get_repo_runs, repo): repo for repo in RUNNER_REPOS}
        for future in as_completed(futures):
            repo, runs = future.result()
            all_runs.extend(runs)

    # Active runs table
    if all_runs:
        table = Table(title="Active / Queued Jobs")
        table.add_column("Repo", style="cyan", max_width=30)
        table.add_column("Status", style="bold")
        table.add_column("Workflow", style="white")
        table.add_column("Branch", style="green")
        table.add_column("Started", style="dim")
        for run in sorted(all_runs, key=lambda r: r["status"]):
            status_style = "bold green" if run["status"] == "in_progress" else "yellow"
            table.add_row(
                run["repo"].replace("ComfyUI-", ""),
                f"[{status_style}]{run['status']}[/{status_style}]",
                run["name"],
                run["branch"],
                run["started"],
            )
        console.print(table)
    else:
        console.print("[dim]No active or queued jobs[/dim]")

    # --- System info from ROADRUNNER ---
    console.print("\n[bold blue]Checking ROADRUNNER...[/bold blue]")

    # Parallel SSH commands
    with ThreadPoolExecutor(max_workers=6) as executor:
        f_win_disk = executor.submit(
            _ssh_cmd,
            'powershell -command "Get-PSDrive C | ForEach-Object { Write-Host ([math]::Round($_.Used/1GB,1)) ([math]::Round($_.Free/1GB,1)) }"'
        )
        f_locks = executor.submit(
            _ssh_cmd,
            'cmd /c "if exist C:\\gpu-lock (type C:\\gpu-lock\\owner 2>nul || echo locked-no-owner) else (echo free)" & '
            'cmd /c "if exist C:\\windows-gpu-lock (echo locked) else (echo free)" & '
            'cmd /c "if exist C:\\windows-portable-gpu-lock (echo locked) else (echo free)" & '
            'cmd /c "if exist C:\\linux-gpu-lock (echo locked) else (echo free)"'
        )
        f_nvidia = executor.submit(
            _ssh_cmd,
            'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits',
            15,
        )
        f_wsl_disk = executor.submit(
            _ssh_cmd,
            'wsl -e df -h / --output=size,used,avail,pcent 2>nul',
            15,
        )
        f_rattler_win = executor.submit(
            _ssh_cmd,
            'powershell -command "'
            '$paths = @(\"$env:USERPROFILE\\.rattler\", \"$env:LOCALAPPDATA\\rattler\", \"C:\\Users\\Administrator\\.rattler\"); '
            'foreach ($p in $paths) { if (Test-Path $p) { $sz = (Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; '
            'Write-Host ([math]::Round($sz/1GB,2)) $p; break } }; '
            '$ce = \"C:\\ce\"; if (Test-Path $ce) { $sz = (Get-ChildItem $ce -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; '
            'Write-Host ([math]::Round($sz/1GB,2)) $ce }'
            '"',
            30,
        )
        f_rattler_wsl = executor.submit(
            _ssh_cmd,
            'wsl -e bash -c "du -sh /home/administrator/.rattler 2>/dev/null; du -sh /home/administrator/.cache/rattler 2>/dev/null; du -sh /home/administrator/.ce 2>/dev/null"',
            15,
        )

    # Parse results
    win_disk = f_win_disk.result()
    locks_raw = f_locks.result()
    nvidia = f_nvidia.result()
    wsl_disk = f_wsl_disk.result()
    rattler_win = f_rattler_win.result()
    rattler_wsl = f_rattler_wsl.result()

    # Disk panel
    disk_lines = []
    if "ERROR" not in win_disk:
        parts = win_disk.split()
        if len(parts) >= 2:
            used, free = parts[0], parts[1]
            total = round(float(used) + float(free), 1)
            pct = round(float(used) / total * 100)
            color = "red" if float(free) < 20 else "yellow" if float(free) < 50 else "green"
            disk_lines.append(f"[bold]Windows C:[/bold]  {used}GB / {total}GB used ([{color}]{free}GB free, {pct}%[/{color}])")
    else:
        disk_lines.append(f"[red]Windows: {win_disk}[/red]")

    if "ERROR" not in wsl_disk and wsl_disk.strip():
        # Parse df output
        lines = [l for l in wsl_disk.strip().split("\n") if l.strip() and not l.strip().startswith("Size")]
        if lines:
            disk_lines.append(f"[bold]WSL:[/bold]        {lines[0].strip()}")
    else:
        disk_lines.append(f"[dim]WSL: unavailable[/dim]")

    # Caches (rattler, CE)
    cache_lines = []
    if "ERROR" not in rattler_win and rattler_win.strip():
        for line in rattler_win.strip().split("\n"):
            parts = line.split(None, 1)
            if len(parts) == 2:
                size, path = parts
                cache_lines.append(f"  [dim]Win:[/dim]  {path} — {size} GB")
    if "ERROR" not in rattler_wsl and rattler_wsl.strip():
        for line in rattler_wsl.strip().split("\n"):
            if line.strip():
                cache_lines.append(f"  [dim]WSL:[/dim]  {line.strip()}")
    if cache_lines:
        disk_lines.append("[bold]Caches:[/bold]")
        disk_lines.extend(cache_lines)

    console.print(Panel("\n".join(disk_lines), title="Disk", border_style="blue"))

    # GPU panel
    gpu_lines = []
    if "ERROR" not in nvidia and nvidia.strip():
        parts = nvidia.split(",")
        if len(parts) >= 3:
            gpu_util, mem_used, mem_total = [p.strip() for p in parts]
            color = "red" if int(gpu_util) > 80 else "yellow" if int(gpu_util) > 20 else "green"
            gpu_lines.append(f"Utilization: [{color}]{gpu_util}%[/{color}]  VRAM: {mem_used}/{mem_total} MiB")
    else:
        gpu_lines.append(f"[dim]{nvidia}[/dim]")
    console.print(Panel("\n".join(gpu_lines), title="GPU", border_style="green"))

    # Locks panel
    lock_lines = []
    if "ERROR" not in locks_raw:
        lock_parts = locks_raw.strip().split("\n")
        lock_names = ["gpu-lock (shared)", "windows-gpu-lock", "windows-portable-gpu-lock", "linux-gpu-lock"]
        for i, name in enumerate(lock_names):
            if i < len(lock_parts):
                status = lock_parts[i].strip()
                if "free" in status:
                    lock_lines.append(f"[green]FREE[/green]    {name}")
                elif "locked-no-owner" in status:
                    lock_lines.append(f"[red]LOCKED[/red]  {name} [dim](no owner file)[/dim]")
                else:
                    lock_lines.append(f"[red]LOCKED[/red]  {name} — [yellow]{status}[/yellow]")
    else:
        lock_lines.append(f"[red]{locks_raw}[/red]")
    console.print(Panel("\n".join(lock_lines), title="Locks", border_style="red"))
