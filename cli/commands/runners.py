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


def _parse_robocopy_output(raw: str) -> list[tuple[str, int]]:
    """Parse robocopy ====path + Bytes output into (path, size_bytes) pairs."""
    results = []
    current_path = None
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line.startswith("===="):
            current_path = line[4:].strip()
        elif "Bytes" in line and ":" in line and current_path:
            # Line like: Bytes : 9725365928 9725365928 0 0 0 0
            parts = line.split(":")
            if len(parts) >= 2:
                nums = parts[1].strip().split()
                if nums:
                    try:
                        results.append((current_path, int(nums[0])))
                    except ValueError:
                        pass
            current_path = None
    return results


def _parse_ce_envs(raw: str, platform: str) -> list[tuple[str, str, float]]:
    """Parse CE env details into (node_name, human_size, sort_bytes) triples.

    For Windows: blocks of ====hash, node_name JSON, robocopy Bytes line.
    For WSL: blocks of ====hash, du -sh output, optional node_name grep.
    """
    results = []
    current_hash = None
    current_name = None
    current_size = None
    current_bytes = 0.0

    for line in raw.strip().split("\n"):
        line = line.strip()
        if line.startswith("===="):
            # Save previous entry
            if current_hash and current_size:
                results.append((current_name or current_hash, current_size, current_bytes))
            current_hash = line[4:].strip()
            current_name = None
            current_size = None
            current_bytes = 0.0
        elif '"node_name"' in line:
            # Extract node name: "node_name": "ComfyUI-TRELLIS2/nodes"
            try:
                val = line.split('"node_name"')[1].split('"')[1]
                # Shorten: ComfyUI-TRELLIS2/nodes -> TRELLIS2/nodes
                val = val.replace("ComfyUI-", "").replace("\\", "/")
                # Collapse double slashes from JSON-escaped backslash
                while "//" in val:
                    val = val.replace("//", "/")
                current_name = val
            except (IndexError, ValueError):
                pass
        elif platform == "win" and "Bytes" in line and ":" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                nums = parts[1].strip().split()
                if nums:
                    try:
                        b = int(nums[0])
                        current_bytes = b
                        current_size = f"{b / (1024**3):.1f}GB"
                    except ValueError:
                        pass
        elif platform == "wsl" and current_hash and not current_size:
            # du -sh output line like: 8.7G\t/path/to/env
            parts = line.split(None, 1)
            if len(parts) >= 1 and any(c.isdigit() for c in parts[0]):
                current_size = parts[0]
                # Parse size for sorting
                sz_str = parts[0].rstrip("GgMmKkTtBb")
                try:
                    val = float(sz_str)
                    if "G" in parts[0].upper():
                        current_bytes = val * 1024**3
                    elif "M" in parts[0].upper():
                        current_bytes = val * 1024**2
                    elif "K" in parts[0].upper():
                        current_bytes = val * 1024
                except ValueError:
                    pass

    # Don't forget last entry
    if current_hash and current_size:
        results.append((current_name or current_hash, current_size, current_bytes))

    return results


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
    host, _, _ = _get_roadrunner_creds()
    console.print(f"\n[bold blue]Checking ROADRUNNER[/bold blue] [dim]({host})[/dim][bold blue]...[/bold blue]")

    # Define all SSH queries with labels for progress tracking
    queries = {
        "win_disk": ("Win disk", _ssh_cmd, (
            'powershell -command "Get-PSDrive C | ForEach-Object { Write-Host ([math]::Round($_.Used/1GB,1)) ([math]::Round($_.Free/1GB,1)) }"',
        ), {}),
        "locks": ("Locks", _ssh_cmd, (
            'cmd /c "if exist C:\\gpu-lock (type C:\\gpu-lock\\owner 2>nul || echo locked-no-owner) else (echo free)" & '
            'cmd /c "if exist C:\\windows-gpu-lock (echo locked) else (echo free)" & '
            'cmd /c "if exist C:\\windows-portable-gpu-lock (echo locked) else (echo free)" & '
            'cmd /c "if exist C:\\linux-gpu-lock (echo locked) else (echo free)"',
        ), {}),
        "nvidia": ("GPU info", _ssh_cmd, (
            'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits',
            15,
        ), {}),
        "gpu_procs": ("GPU processes", _ssh_cmd, (
            'nvidia-smi --query-compute-apps=pid,used_gpu_memory,process_name --format=csv,noheader,nounits',
            15,
        ), {}),
        "wsl_disk": ("WSL disk", _ssh_cmd, (
            'wsl -e df -h / --output=size,used,avail,pcent 2>nul',
            15,
        ), {}),
        "caches_wsl": ("WSL caches", _ssh_cmd, (
            'wsl -- bash -c "du -sh'
            ' /home/administrator/.ce'
            ' /home/administrator/.rattler'
            ' /home/administrator/.cache/rattler'
            ' /home/administrator/.cache/uv'
            ' /home/administrator/.cache/pip'
            ' 2>/dev/null; true"',
            90,
        ), {}),
        "caches_win": ("Win caches", _ssh_cmd, (
            'cmd /c "for %d in ('
            "C:\\ce "
            "C:\\Users\\Administrator\\.rattler "
            "C:\\Users\\Administrator\\AppData\\Local\\rattler "
            "C:\\Users\\Administrator\\AppData\\Local\\uv "
            "C:\\Users\\Administrator\\AppData\\Local\\pip"
            ') do @if exist %d ('
            'echo ====%d '
            "& robocopy %d %d\\..\\__fake /L /S /NJH /NFL /NDL /BYTES /R:0 /W:0 2>nul"
            ')"',
            120,
        ), {}),
        "xwayland": ("Xwayland", _ssh_cmd, (
            'wsl -- bash -c "pgrep Xwayland >/dev/null 2>&1 && echo RUNNING || echo NOT_RUNNING"',
            10,
        ), {}),
        "runners_wsl": ("WSL runner folders", _ssh_cmd, (
            'wsl -- bash -c "du -sh /home/administrator/github-runners/PozzettiAndrea-*/_work 2>/dev/null; true"',
            90,
        ), {}),
        "runners_win": ("Win runner folders", _ssh_cmd, (
            'cmd /c "for /d %d in (C:\\github-runners\\PozzettiAndrea-*) do @if exist %d\\_work ('
            'echo ====%d '
            "& robocopy %d\\_work %d\\_work\\..\\__fake /L /S /NJH /NFL /NDL /BYTES /R:0 /W:0 2>nul"
            ')"',
            120,
        ), {}),
        "ce_envs_win": ("Win CE envs", _ssh_cmd, (
            'cmd /c "for /d %d in (C:\\ce\\_env_*) do @('
            'echo ====%~nxd '
            '& type %d\\.comfy-env-meta.json 2>nul '
            '& robocopy %d %d\\..\\__fake /L /S /NJH /NFL /NDL /BYTES /R:0 /W:0 2>nul'
            ')"',
            120,
        ), {}),
        "ce_envs_wsl": ("WSL CE envs", _ssh_cmd, (
            r'wsl -- bash -c "for d in /home/administrator/.ce/_env_*/; do echo ====\$(basename \$d); du -sh \$d 2>/dev/null; grep node_name \$d/.comfy-env-meta.json 2>/dev/null; done"',
            90,
        ), {}),
    }

    # Launch all SSH commands in parallel with live progress
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_key = {}
        for key, (label, func, args, kwargs) in queries.items():
            future = executor.submit(func, *args, **kwargs)
            future_to_key[future] = key

        pending = {k: v[0] for k, v in queries.items()}  # key -> label
        with console.status("") as status:
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                results[key] = future.result()
                del pending[key]
                if pending:
                    waiting = ", ".join(pending.values())
                    status.update(f"[dim]waiting:[/dim] {waiting}")

    win_disk = results["win_disk"]
    locks_raw = results["locks"]
    nvidia = results["nvidia"]
    gpu_procs = results["gpu_procs"]
    wsl_disk = results["wsl_disk"]
    caches_win = results["caches_win"]
    caches_wsl = results["caches_wsl"]
    xwayland = results["xwayland"]
    runners_win = results["runners_win"]
    runners_wsl = results["runners_wsl"]
    ce_envs_win = results["ce_envs_win"]
    ce_envs_wsl = results["ce_envs_wsl"]

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

    console.print(Panel("\n".join(disk_lines), title="Disk", border_style="blue"))

    # Caches panel
    cache_lines = []
    # Parse robocopy output: ====path\n   Bytes : 123456 ...
    if "ERROR" not in caches_win and caches_win.strip():
        for path, size_bytes in _parse_robocopy_output(caches_win):
            sz_gb = round(size_bytes / (1024**3), 1)
            if sz_gb > 0:
                name = path.rstrip("\\").split("\\")[-1]
                color = "red" if sz_gb >= 10 else "yellow" if sz_gb >= 2 else "dim"
                # For CE, show env breakdown instead of just total
                if name == "ce" or name == ".ce":
                    win_envs = _parse_ce_envs(ce_envs_win, "win") if "ERROR" not in ce_envs_win and ce_envs_win.strip() else []
                    if win_envs:
                        cache_lines.append(f"  [dim]Win:[/dim]  [{color}]{sz_gb}GB[/{color}]  CE ({len(win_envs)} envs)")
                        for env_name, env_size, _ in sorted(win_envs, key=lambda x: x[2], reverse=True):
                            cache_lines.append(f"         [dim]{env_size:>7}  {env_name}[/dim]")
                    else:
                        cache_lines.append(f"  [dim]Win:[/dim]  [{color}]{sz_gb}GB[/{color}]  CE [dim]({path})[/dim]")
                else:
                    cache_lines.append(f"  [dim]Win:[/dim]  [{color}]{sz_gb}GB[/{color}]  {name} [dim]({path})[/dim]")
    if "ERROR" not in caches_wsl and caches_wsl.strip():
        for line in caches_wsl.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                size, path = parts
                name = path.rstrip("/").split("/")[-1]
                sz_str = size.rstrip("GgMmKkTt")
                try:
                    sz_val = float(sz_str)
                    is_gb = "G" in size.upper()
                    color = "red" if (is_gb and sz_val >= 10) else "yellow" if (is_gb and sz_val >= 2) else "dim"
                except ValueError:
                    color = "dim"
                # For CE, show env breakdown instead of just total
                if name == ".ce" or name == "ce":
                    wsl_envs = _parse_ce_envs(ce_envs_wsl, "wsl") if "ERROR" not in ce_envs_wsl and ce_envs_wsl.strip() else []
                    if wsl_envs:
                        cache_lines.append(f"  [dim]WSL:[/dim]  [{color}]{size}[/{color}]  CE ({len(wsl_envs)} envs)")
                        for env_name, env_size, _ in sorted(wsl_envs, key=lambda x: x[2], reverse=True):
                            cache_lines.append(f"         [dim]{env_size:>7}  {env_name}[/dim]")
                    else:
                        cache_lines.append(f"  [dim]WSL:[/dim]  [{color}]{size}[/{color}]  CE [dim]({path})[/dim]")
                else:
                    cache_lines.append(f"  [dim]WSL:[/dim]  [{color}]{size}[/{color}]  {name} [dim]({path})[/dim]")
    if cache_lines:
        console.print(Panel("\n".join(cache_lines), title="Caches", border_style="yellow"))
    else:
        errs = []
        if "ERROR" in caches_win:
            errs.append(f"Win: {caches_win}")
        if "ERROR" in caches_wsl:
            errs.append(f"WSL: {caches_wsl}")
        if errs:
            console.print(Panel("[red]timed out[/red]\n" + "\n".join(f"[dim]{e}[/dim]" for e in errs), title="Caches", border_style="yellow"))
        else:
            console.print(Panel("[dim]no caches found[/dim]", title="Caches", border_style="yellow"))

    # Runner _work folders panel
    runner_lines = []
    # Parse robocopy output for Win runners
    if "ERROR" not in runners_win and runners_win.strip():
        for path, size_bytes in _parse_robocopy_output(runners_win):
            sz_gb = round(size_bytes / (1024**3), 1)
            name = path.rstrip("\\").split("\\")[-1].replace("PozzettiAndrea-", "")
            color = "red" if sz_gb >= 5 else "yellow" if sz_gb >= 1 else "dim"
            runner_lines.append(f"  [dim]Win:[/dim]  [{color}]{sz_gb}GB[/{color}]  {name}")
    if "ERROR" not in runners_wsl and runners_wsl.strip():
        for line in runners_wsl.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                size, path = parts
                # Extract runner name from path like .../PozzettiAndrea-ComfyUI-FOO/_work
                name = path.rstrip("/").replace("/_work", "").split("/")[-1].replace("PozzettiAndrea-", "")
                sz_str = size.rstrip("GgMmKkTt")
                try:
                    sz_val = float(sz_str)
                    is_gb = "G" in size.upper()
                    color = "red" if (is_gb and sz_val >= 5) else "yellow" if (is_gb and sz_val >= 1) else "dim"
                except ValueError:
                    color = "dim"
                runner_lines.append(f"  [dim]WSL:[/dim]  [{color}]{size}[/{color}]  {name}")
    if runner_lines:
        console.print(Panel("\n".join(runner_lines), title="Runner _work Folders", border_style="cyan"))
    else:
        console.print(Panel("[dim]all empty[/dim]", title="Runner _work Folders", border_style="cyan"))

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
    # GPU compute processes (filter out [N/A] entries which are display processes)
    if "ERROR" not in gpu_procs and gpu_procs.strip():
        compute_procs = []
        for line in gpu_procs.strip().split("\n"):
            if "[N/A]" in line or not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                pid, mem, proc = parts[0], parts[1], parts[2]
                proc_short = proc.split("/")[-1].split("\\")[-1]
                compute_procs.append(f"  PID {pid}  {mem} MiB  {proc_short}")
        if compute_procs:
            gpu_lines.append("[bold]Compute processes:[/bold]")
            gpu_lines.extend(compute_procs)
    console.print(Panel("\n".join(gpu_lines), title="GPU", border_style="green"))

    # Services panel (Xwayland etc.)
    svc_lines = []
    if "ERROR" not in xwayland:
        xw = xwayland.strip()
        if "RUNNING" in xw and "NOT" not in xw:
            svc_lines.append("[green]Xwayland: running[/green]")
        else:
            svc_lines.append("[red]Xwayland: NOT RUNNING[/red]")
    else:
        svc_lines.append(f"[red]Xwayland: unknown[/red] [dim]({xwayland})[/dim]")
    console.print(Panel("\n".join(svc_lines), title="Services", border_style="magenta"))

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
