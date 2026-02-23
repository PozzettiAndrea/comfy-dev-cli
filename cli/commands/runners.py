"""Monitor self-hosted GitHub runners on ROADRUNNER."""

import json
import subprocess
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

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

# Map step names to high-level stages
STAGE_MAP = {
    "Acquire platform lock": "waiting platform lock",
    "Acquire GPU lock": "waiting GPU lock",
    "Run tests": "running tests",
    "Release GPU lock": "releasing GPU lock",
    "Release platform lock": "releasing platform lock",
    "Cleanup workspace": "cleaning up",
    "Cleanup stale VHDs": "setup",
    "Cleanup stale mounts": "setup",
    "Setup Python": "setup",
    "Setup environment": "setup",
    "Set cache directory": "setup",
    "Restore local cache": "setup",
    "Save local cache": "setup",
    "Verify CUDA torch": "setup",
    "Install comfy-test": "installing",
    "Install node dependencies": "installing deps",
    "Install validate endpoint": "installing",
    "Download portable ComfyUI": "setup",
    "Extract portable ComfyUI": "setup",
    "Install Playwright browsers": "setup",
    "Start ComfyUI server": "starting server",
    "Wait for server": "starting server",
    "Free disk space": "setup",
    "Clone ComfyUI": "setup",
    "Install ComfyUI requirements": "setup",
    "Create venv and install uv": "setup",
    "Verify base setup": "setup",
}


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


def _parse_ts(ts: str | None) -> datetime | None:
    """Parse a GitHub API timestamp."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _duration_str(start: datetime | None) -> str:
    """Human-readable duration from start to now."""
    if not start:
        return ""
    delta = datetime.now(timezone.utc) - start
    secs = int(delta.total_seconds())
    if secs < 0:
        return "0s"
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m{secs % 60:02d}s"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"


def _get_job_stage(job: dict) -> tuple[str, str, datetime | None]:
    """Determine current stage, step name, and step start time from a job's steps.

    Returns (stage, step_name, started_at).
    """
    steps = job.get("steps", [])
    # Find the in_progress step
    for step in steps:
        if step.get("status") == "in_progress":
            name = step["name"]
            stage = STAGE_MAP.get(name, name.lower())
            return stage, name, _parse_ts(step.get("started_at"))

    # No in_progress step — find last completed
    last_completed = None
    for step in steps:
        if step.get("status") == "completed":
            last_completed = step
    if last_completed:
        name = last_completed["name"]
        return f"after {STAGE_MAP.get(name, name.lower())}", name, _parse_ts(last_completed.get("completed_at"))

    return "queued", "", None


def _get_repo_jobs(repo: str) -> tuple[str, list]:
    """Get per-job details for active runs in a repo."""
    jobs = []
    for status in ["in_progress", "queued"]:
        data = _gh_api(f"repos/{GITHUB_OWNER}/{repo}/actions/runs?status={status}&per_page=5")
        if not data or "workflow_runs" not in data:
            continue
        for run in data["workflow_runs"]:
            run_id = run["id"]
            branch = run.get("head_branch", "?")
            run_url = run["html_url"]
            run_started = _parse_ts(run.get("run_started_at"))

            # Fetch jobs for this run
            jobs_data = _gh_api(f"repos/{GITHUB_OWNER}/{repo}/actions/runs/{run_id}/jobs?per_page=30")
            if not jobs_data or "jobs" not in jobs_data:
                continue
            for job in jobs_data["jobs"]:
                job_name = job["name"]
                job_status = job["status"]
                conclusion = job.get("conclusion")  # success/failure/cancelled/null
                job_started = _parse_ts(job.get("started_at"))

                # Skip the "setup" meta-job
                if job_name.endswith("/ setup") or job_name == "setup":
                    continue

                # Only GPU jobs run on self-hosted ROADRUNNER
                is_self_hosted = "gpu" in job_name.lower() and "cpu" not in job_name.lower()

                # Get current stage from steps (or conclusion for completed)
                if job_status == "completed":
                    stage = conclusion or "done"
                    step_name = ""
                    step_started = None
                else:
                    stage, step_name, step_started = _get_job_stage(job)

                jobs.append({
                    "repo": repo,
                    "branch": branch,
                    "job_name": job_name,
                    "job_status": job_status,
                    "conclusion": conclusion,
                    "self_hosted": is_self_hosted,
                    "stage": stage,
                    "step_name": step_name,
                    "step_started": step_started,
                    "job_started": job_started,
                    "run_started": run_started,
                    "run_id": run_id,
                    "job_id": job["id"],
                    "url": run_url,
                })
    return repo, jobs


def _format_stage(job: dict) -> str:
    """Format stage with colors."""
    stage = job["stage"]
    if stage == "success":
        return "[green]pass[/green]"
    if stage == "failure":
        return "[bold red]FAIL[/bold red]"
    if stage == "cancelled":
        return "[dim]cancelled[/dim]"
    if "waiting GPU lock" in stage:
        return f"[yellow]{stage}[/yellow]"
    if "waiting platform lock" in stage:
        return f"[yellow]{stage}[/yellow]"
    if "running tests" in stage:
        test_dur = _duration_str(job["step_started"]) if job["step_started"] else ""
        return f"[bold green]{stage}[/bold green] [dim]({test_dur})[/dim]" if test_dur else f"[bold green]{stage}[/bold green]"
    if stage in ("setup", "installing", "installing deps"):
        return f"[dim]{stage}[/dim]"
    if stage == "queued":
        return f"[dim yellow]{stage}[/dim yellow]"
    return stage


def monitor_runners():
    """Show runner status, active jobs, disk space, and locks."""

    # --- Per-job details across all repos (parallel) ---
    console.print("[bold blue]Fetching runner activity...[/bold blue]")
    all_jobs = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_get_repo_jobs, repo): repo for repo in RUNNER_REPOS}
        for future in as_completed(futures):
            repo, jobs = future.result()
            all_jobs.extend(jobs)

    # Split GPU (self-hosted) vs CPU (cloud)
    self_hosted = [j for j in all_jobs if j["self_hosted"]]
    cloud = [j for j in all_jobs if not j["self_hosted"]]

    # Self-hosted runners table (the main focus)
    if self_hosted:
        table = Table(title="Self-Hosted Jobs (ROADRUNNER)")
        table.add_column("Repo", style="cyan", max_width=20)
        table.add_column("Job", style="white", max_width=28)
        table.add_column("Stage", style="bold")
        table.add_column("Duration", justify="right", style="dim")
        table.add_column("Run ID", style="dim")
        table.add_column("Job ID", style="dim")
        for job in sorted(self_hosted, key=lambda j: (j["repo"], j["job_name"])):
            stage_display = _format_stage(job)
            duration = _duration_str(job["job_started"]) if job["job_started"] else _duration_str(job["run_started"])

            jn = job["job_name"]
            if "/" in jn:
                parts = [p.strip() for p in jn.split("/")]
                jn = parts[1] if len(parts) > 1 else parts[0]

            table.add_row(
                job["repo"].replace("ComfyUI-", ""),
                jn,
                stage_display,
                duration,
                str(job["run_id"]),
                str(job["job_id"]),
            )
        console.print(table)
    else:
        console.print("[dim]No self-hosted jobs running[/dim]")

    # Cloud runners (CPU jobs)
    if cloud:
        table = Table(title="Cloud Jobs (GitHub-hosted)", style="dim")
        table.add_column("Repo", style="cyan", max_width=20)
        table.add_column("Job", style="white", max_width=28)
        table.add_column("Stage")
        table.add_column("Duration", justify="right")
        table.add_column("Run ID")
        table.add_column("Job ID")
        for job in sorted(cloud, key=lambda j: (j["repo"], j["job_name"])):
            stage_display = _format_stage(job)
            duration = _duration_str(job["job_started"]) if job["job_started"] else _duration_str(job["run_started"])
            jn = job["job_name"]
            if "/" in jn:
                parts = [p.strip() for p in jn.split("/")]
                jn = parts[1] if len(parts) > 1 else parts[0]
            table.add_row(
                job["repo"].replace("ComfyUI-", ""),
                jn,
                stage_display,
                duration,
                str(job["run_id"]),
                str(job["job_id"]),
            )
        console.print(table)

    if not self_hosted and not cloud:
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
