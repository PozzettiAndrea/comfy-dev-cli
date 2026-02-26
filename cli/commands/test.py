"""Run comfy-test locally. Auto-detects OS."""
import os
import platform
import subprocess
import shutil
from pathlib import Path
from rich.console import Console
import yaml
from commands.clone_utils import clone_utils_repos
from commands.get import setup_comfyui, CONFIG_DIR, INSTALL_DIR
from config import UTILS_REPOS_DIR, COMMAND_NAME

console = Console()


def ensure_comfy_test_installed() -> bool:
    """Ensure comfy-test is installed as a uv tool."""
    # Check if comfy-test is already available
    if shutil.which("comfy-test") is not None:
        return True

    comfy_test_path = UTILS_REPOS_DIR / "comfy-test"

    # Check if utils/comfy-test exists, clone if not
    if not comfy_test_path.exists():
        console.print("[yellow]Utils folder missing, cloning...[/yellow]")
        clone_utils_repos()

    # Install comfy-test as a uv tool (like cds itself)
    console.print("[yellow]Installing comfy-test as uv tool...[/yellow]")
    result = subprocess.run(
        ["uv", "tool", "install", "-e", str(comfy_test_path), "--force"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Failed to install comfy-test: {result.stderr}[/red]")
        return False
    console.print("[green]comfy-test installed successfully[/green]")
    return True


def run_test(
    repo_name: str,
    gpu: bool = False,
    portable: bool = False,
    verbose: bool = False,
    workflow: str = None,
    force: bool = False,
    novram: bool = False,
    full_mem_log: bool = False,
) -> int:
    """Run comfy-test locally."""
    if not ensure_comfy_test_installed():
        return 1

    repo_path = find_repo(repo_name)
    if not repo_path:
        return 1

    # Determine platform
    is_windows = platform.system() == "Windows"
    if is_windows:
        platform_name = "windows-portable" if portable else "windows"
    else:
        platform_name = "linux"

    return run_direct(repo_path, platform_name=platform_name, gpu=gpu, verbose=verbose, workflow=workflow, force=force, novram=novram, full_mem_log=full_mem_log)


def find_repo(repo_name: str) -> Path | None:
    """Find repository in cds get environment, setting up if needed.

    Uses the structure: ~/{config_name}/ComfyUI/custom_nodes/{node_name}/
    This enables live debugging in a real ComfyUI environment.
    """
    # Normalize config name (lowercase, no prefix)
    config_name = repo_name.lower().replace("comfyui-", "").replace("-", "")

    # Find matching config file
    config_file = None
    for f in CONFIG_DIR.glob("*.yml"):
        if f.stem.lower().replace("-", "") == config_name:
            config_file = f
            break

    if not config_file:
        console.print(f"[red]No setup config found for: {repo_name}[/red]")
        console.print(f"[dim]Looked in: {CONFIG_DIR}[/dim]")
        available = sorted([f.stem for f in CONFIG_DIR.glob("*.yml")])
        if available:
            console.print(f"[dim]Available: {', '.join(available[:10])}[/dim]")
        return None

    # Load config to get folder name and node URL
    with open(config_file) as f:
        config = yaml.safe_load(f)

    folder_name = config.get("folder_name", config_file.stem)
    nodes_to_install = config.get("nodes_to_install", [])

    # Get the node name from the first node URL
    if not nodes_to_install:
        console.print(f"[red]No nodes_to_install in config: {config_file}[/red]")
        return None

    first_node = nodes_to_install[0]
    if isinstance(first_node, dict):
        node_url = first_node.get("url", "")
    else:
        node_url = first_node

    node_name = node_url.rstrip("/").split("/")[-1].replace(".git", "")

    # Expected path: {INSTALL_DIR}/{folder_name}/ComfyUI/custom_nodes/{node_name}/
    install_path = INSTALL_DIR / folder_name
    repo_path = install_path / "ComfyUI" / "custom_nodes" / node_name

    # Check if environment exists
    if not repo_path.exists():
        console.print(f"[yellow]Environment not set up: {install_path}[/yellow]")
        console.print(f"[cyan]Running {COMMAND_NAME} get {config_file.stem} --reinstall...[/cyan]")
        setup_comfyui(config_file.stem, reinstall=True)  # Fresh install for safety

        # Verify it exists now
        if not repo_path.exists():
            console.print(f"[red]Setup completed but repo not found: {repo_path}[/red]")
            return None

    # Verify comfy-test.toml exists
    if not (repo_path / "comfy-test.toml").exists():
        console.print(f"[red]No comfy-test.toml in {repo_path}[/red]")
        return None

    console.print(f"[dim]Using: {repo_path}[/dim]")
    return repo_path


def get_platform_suffix(platform_name: str, gpu: bool) -> str:
    """Return platform suffix like 'linux-cpu' or 'windows-portable-gpu'."""
    gpu_mode = "gpu" if gpu else "cpu"
    return f"{platform_name}-{gpu_mode}"


def get_git_branch(repo_path: Path) -> str:
    """Get current git branch name, default to 'dev' if not in git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "dev"


def run_direct(repo_path: Path, platform_name: str = "windows", gpu: bool = False, verbose: bool = False, workflow: str = None, force: bool = False, novram: bool = False, full_mem_log: bool = False) -> int:
    """Run comfy-test directly without Docker (Windows)."""
    from datetime import datetime

    mode = "GPU" if gpu else "CPU"
    console.print(f"[bold cyan]Running comfy-test directly ({platform_name}, {mode} mode)[/bold cyan]")

    # Use COMFY_TEST_LOGS_DIR if set, otherwise default to ~/logs or ~/Desktop/logs
    logs_dir_env = os.environ.get("COMFY_TEST_LOGS_DIR")
    if logs_dir_env:
        logs_dir = Path(logs_dir_env)
    elif platform.system() == "Windows":
        logs_dir = Path.home() / "Desktop" / "logs"
    else:
        logs_dir = Path.home() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    repo_short = repo_path.name.replace("ComfyUI-", "")
    timestamp = datetime.now().strftime("%H%M")
    platform_suffix = get_platform_suffix(platform_name, gpu)
    branch = get_git_branch(repo_path)

    parent_dir = logs_dir / f"{repo_short}-{timestamp}"
    output_dir = parent_dir / branch / platform_suffix
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[dim]Output: {output_dir}[/dim]")

    # Set env vars for comfy-test (only if not already set)
    if "COMFY_TEST_LOGS_DIR" not in os.environ:
        os.environ["COMFY_TEST_LOGS_DIR"] = str(logs_dir)
    if "COMFY_TEST_WORKSPACE_DIR" not in os.environ:
        os.environ["COMFY_TEST_WORKSPACE_DIR"] = str(logs_dir.parent / "workspaces")
    if gpu:
        os.environ["COMFY_TEST_GPU"] = "1"

    # Build comfy-test command
    cmd = ["comfy-test", "run", "--platform", platform_name, "--branch", branch]
    if gpu:
        cmd.append("--gpu")
    if verbose:
        cmd.append("--verbose")
    if workflow:
        cmd.extend(["--workflow", workflow])
    if force:
        cmd.append("--force")
    if novram:
        cmd.append("--novram")
    if full_mem_log:
        cmd.append("--full-mem-log")

    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")

    # Run directly - output goes to console, tee to log file
    result = subprocess.run(cmd, cwd=repo_path)

    # Copy results to output dir if they exist
    results_dir = repo_path / ".comfy-test"
    if results_dir.exists():
        import shutil
        for item in results_dir.iterdir():
            dest = output_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        console.print(f"[green]Results copied to {output_dir}[/green]")

    return result.returncode
