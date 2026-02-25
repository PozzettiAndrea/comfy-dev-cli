"""Start ComfyUI in a virtual environment."""
import subprocess
import socket
import platform
import time
from pathlib import Path
from rich.console import Console

from config import CT_ENVS_DIR, INSTALL_DIR, get_logger, COMMAND_NAME

console = Console()
IS_WINDOWS = platform.system() == "Windows"
logger = None


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_available_port(start_port: int = 8188, step: int = 100, max_attempts: int = 10) -> int:
    """Find the first available port starting from start_port, incrementing by step."""
    port = start_port
    for _ in range(max_attempts):
        if not is_port_in_use(port):
            return port
        port += step
    return port


def wait_for_port(port: int, poll_interval: float = 2.0) -> None:
    """Block until the given port becomes free."""
    console.print(f"[yellow]Port {port} in use, waiting for it to become free...[/yellow]")
    while is_port_in_use(port):
        time.sleep(poll_interval)
    console.print(f"[green]Port {port} is now free[/green]")


def start_comfyui(repo_name: str, port: int = None, cpu: bool = False, novram: bool = False) -> int:
    """Start ComfyUI in a virtual environment."""
    global logger
    logger = get_logger("start")

    port_explicit = port is not None
    if port is None:
        port = 8188

    # Find the repo directory (Desktop on Windows, home on Linux)
    repo_path = INSTALL_DIR / repo_name / "ComfyUI"

    if not repo_path.exists():
        console.print(f"[red]ComfyUI not found at {repo_path}[/red]")
        console.print(f"[dim]Run: {COMMAND_NAME} get {repo_name}[/dim]")
        return 1

    main_py = repo_path / "main.py"
    if not main_py.exists():
        console.print(f"[red]main.py not found in {repo_path}[/red]")
        return 1

    # Find the venv python
    env_path = CT_ENVS_DIR / repo_name
    if IS_WINDOWS:
        env_python = env_path / "Scripts" / "python.exe"
    else:
        env_python = env_path / "bin" / "python"

    if not env_python.exists():
        console.print(f"[red]Virtual environment not found at {env_path}[/red]")
        console.print(f"[dim]Run: {COMMAND_NAME} get {repo_name}[/dim]")
        return 1

    if port_explicit:
        # User asked for a specific port — wait for it
        if is_port_in_use(port):
            wait_for_port(port)
    else:
        # No port specified — slide to next available
        original_port = port
        port = find_available_port(start_port=port)
        if port != original_port:
            console.print(f"[yellow]Port {original_port} in use, using {port}[/yellow]")

    console.print(f"[cyan]Starting ComfyUI[/cyan]")
    console.print(f"[dim]Env: {repo_name}[/dim]")
    console.print(f"[dim]Port: {port}[/dim]")
    console.print(f"[dim]Path: {repo_path}[/dim]")
    if cpu:
        console.print(f"[dim]Mode: CPU[/dim]")
    if novram:
        console.print(f"[dim]Mode: NOVRAM[/dim]")
    console.print()

    # Run directly with venv python
    cmd = [str(env_python), "main.py", "--port", str(port), "--listen", "0.0.0.0"]
    if cpu:
        cmd.append("--cpu")
    if novram:
        cmd.append("--novram")

    logger.info(f"Starting ComfyUI: {' '.join(cmd)}")
    logger.info(f"Working directory: {repo_path}")

    try:
        # Use Popen to stream output to both terminal and log file
        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
        )

        # Stream output line by line
        for line in process.stdout:
            line = line.rstrip()
            print(line)
            logger.info(line)

        process.wait()
        logger.info(f"ComfyUI exited with code {process.returncode}")
        return process.returncode
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")
        logger.info("ComfyUI stopped by user (KeyboardInterrupt)")
        return 0
