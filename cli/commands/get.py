"""ComfyUI environment setup from YAML configs."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from rich.console import Console

from config import UTILS_REPOS_DIR, CT_ENVS_DIR, INSTALL_DIR, get_logger, COMMAND_NAME

console = Console()
IS_WINDOWS = platform.system() == "Windows"
logger = None  # Initialized in setup_comfyui


def force_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files on Windows."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def run_logged(cmd: list, check: bool = True, cwd=None) -> subprocess.CompletedProcess:
    """Run a subprocess, streaming output to terminal and logging it."""
    global logger
    cmd_str = " ".join(str(c) for c in cmd)
    if logger:
        logger.info(f"Running: {cmd_str}")

    # Use Popen to stream output in real-time
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
        cwd=cwd,
        bufsize=1,  # Line buffered
    )

    # Stream output line by line
    output_lines = []
    for line in process.stdout:
        line = line.rstrip()
        print(line)  # Print to terminal
        output_lines.append(line)
        if logger:
            logger.info(line)

    process.wait()

    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    # Return a CompletedProcess-like result
    return subprocess.CompletedProcess(cmd, process.returncode, "\n".join(output_lines), "")


# Paths - use fixed location so it works when installed globally
CONFIG_DIR = Path.home() / "coding-scripts" / "comfy-dev-cli" / "config" / "setup"


def list_configs():
    """List available ComfyUI configs."""
    configs = sorted([f.stem for f in CONFIG_DIR.glob("*.yml")])
    console.print("[bold]Available configs:[/bold]")
    for name in configs:
        console.print(f"  [cyan]{name}[/cyan]")
    console.print()
    console.print(f"Usage: [green]{COMMAND_NAME} get <config_name>[/green]")


def setup_comfyui(config_name: str, reinstall: bool = False):
    """Set up a ComfyUI environment from a YAML config."""
    global logger
    logger = get_logger("get")
    logger.info(f"Starting setup for config: {config_name}")

    config_file = CONFIG_DIR / f"{config_name}.yml"

    if not config_file.exists():
        console.print(f"[red]Error: Config file not found: {config_file}[/red]")
        available = [f.stem for f in CONFIG_DIR.glob("*.yml")]
        console.print(f"Available configs: {', '.join(sorted(available))}")
        raise SystemExit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    folder_name = config["folder_name"]
    env_name = config["conda_env_name"]  # Keep using this field name for compatibility
    nodes_to_install = config.get("nodes_to_install", [])

    install_path = INSTALL_DIR / folder_name
    comfyui_path = install_path / "ComfyUI"

    # Check uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[red]Error: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh[/red]")
        raise SystemExit(1)

    # Environment path in central location
    env_path = CT_ENVS_DIR / env_name

    # Handle --reinstall
    if reinstall:
        console.print("[yellow]=== REINSTALL MODE ===[/yellow]")
        if install_path.exists():
            console.print(f"Deleting existing folder: {install_path}")
            shutil.rmtree(install_path, onerror=force_remove_readonly)

        if env_path.exists():
            console.print(f"Removing existing venv: {env_path}")
            shutil.rmtree(env_path, onerror=force_remove_readonly)
        console.print("[yellow]======================[/yellow]")

    console.print(f"Setting up ComfyUI in [cyan]{install_path}[/cyan] with venv [cyan]{env_name}[/cyan]")

    # Create directory and clone repos
    install_path.mkdir(parents=True, exist_ok=True)
    os.chdir(install_path)

    if not comfyui_path.exists():
        console.print("Cloning ComfyUI...")
        run_logged(["git", "clone", "--depth", "1", "https://github.com/comfyanonymous/ComfyUI.git"])

    custom_nodes_path = comfyui_path / "custom_nodes"
    manager_path = custom_nodes_path / "ComfyUI-Manager"
    if not manager_path.exists():
        console.print("Cloning ComfyUI-Manager...")
        os.chdir(custom_nodes_path)
        run_logged(["git", "clone", "--depth", "1", "https://github.com/Comfy-Org/ComfyUI-Manager.git"])

    os.chdir(comfyui_path)

    # Pin torch version in requirements.txt
    requirements_file = comfyui_path / "requirements.txt"
    if requirements_file.exists():
        content = requirements_file.read_text()
        if "\ntorch\n" in content or content.startswith("torch\n"):
            console.print("Pinning torch version to 2.8.0...")
            content = content.replace("\ntorch\n", "\ntorch==2.8.0\n").replace("torch\n", "torch==2.8.0\n", 1)
            requirements_file.write_text(content)

    # Create virtual environment with uv
    CT_ENVS_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"Creating virtual environment [cyan]{env_name}[/cyan]...")
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    run_logged(["uv", "venv", str(env_path), "--python", py_version])

    # Get the python path for the new env
    if IS_WINDOWS:
        env_python = env_path / "Scripts" / "python.exe"
    else:
        env_python = env_path / "bin" / "python"

    # Install PyTorch with CUDA support first (before requirements.txt)
    console.print("Installing PyTorch with CUDA support...")
    run_logged([
        "uv", "pip", "install",
        "torch==2.8.0", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu128",
        "--python", str(env_python)
    ])

    # Install ComfyUI-Manager requirements
    manager_reqs = manager_path / "requirements.txt"
    if manager_reqs.exists():
        console.print("Installing ComfyUI-Manager requirements...")
        run_logged(["uv", "pip", "install", "-r", str(manager_reqs), "--python", str(env_python)])

    # Install ComfyUI requirements (torch already installed with CUDA)
    console.print("Installing ComfyUI requirements...")
    run_logged(["uv", "pip", "install", "-r", str(requirements_file), "--python", str(env_python)])

    # Install local dev packages EARLY (so install.py uses local version with fixes)
    console.print("Installing local dev packages (editable)...")
    utils_dir = UTILS_REPOS_DIR
    for pkg in ["comfy-env", "comfy-test", "comfy-3d-viewers", "comfy-attn"]:
        pkg_path = utils_dir / pkg
        if pkg_path.exists():
            run_logged(["uv", "pip", "install", "-e", str(pkg_path), "--python", str(env_python)])

    # Create constraints file to protect local packages from being overwritten
    constraints_file = env_path / "constraints.txt"
    constraints = []
    for pkg in ["comfy-env", "comfy-test", "comfy-3d-viewers", "comfy-attn"]:
        pkg_path = utils_dir / pkg
        if pkg_path.exists():
            constraints.append(f"{pkg} @ file://{pkg_path}")
    if constraints:
        constraints_file.write_text("\n".join(constraints) + "\n")
        console.print(f"[dim]Created constraints file: {constraints_file}[/dim]")

    # Install custom nodes
    console.print("Installing custom nodes...")
    for node in nodes_to_install:
        if isinstance(node, dict):
            url = node.get("url", "")
            branch = node.get("branch", "dev")
        else:
            url = node
            branch = "dev"

        if not url:
            continue

        name = url.rstrip("/").split("/")[-1].replace(".git", "")
        target = custom_nodes_path / name

        branch_info = f" (branch: {branch})" if branch else ""
        console.print(f"  Installing [cyan]{name}[/cyan]{branch_info}")

        if target.exists():
            console.print(f"    [yellow]Already exists, skipping clone[/yellow]")
        else:
            clone_cmd = ["git", "clone", "--depth", "1"]
            if branch:
                clone_cmd.extend(["-b", branch])
            clone_cmd.extend([url, str(target)])
            run_logged(clone_cmd)

        # Install requirements first (provides dependencies for install.py)
        # Use constraints file to prevent local packages from being overwritten
        node_reqs = target / "requirements.txt"
        if node_reqs.exists():
            pip_cmd = ["uv", "pip", "install", "-r", str(node_reqs), "--python", str(env_python)]
            if constraints_file.exists():
                pip_cmd.extend(["--overrides", str(constraints_file)])
            run_logged(pip_cmd, check=False)

        # Run install.py after requirements are installed
        install_script = target / "install.py"
        if install_script.exists():
            run_logged([str(env_python), str(install_script)], check=False, cwd=target)

    # Also install in any isolated _env_* environments created by custom nodes
    for env_dir in custom_nodes_path.glob("*/_env_*"):
        if env_dir.is_dir() or env_dir.is_symlink():
            # Find pip in the isolated env
            isolated_pip = env_dir / "bin" / "pip"
            if not isolated_pip.exists():
                isolated_pip = env_dir / "Scripts" / "pip.exe"  # Windows
            if isolated_pip.exists():
                console.print(f"  Installing in isolated env: [cyan]{env_dir.name}[/cyan]")
                for pkg in ["comfy-env", "comfy-test", "comfy-3d-viewers", "comfy-attn"]:
                    pkg_path = utils_dir / pkg
                    if pkg_path.exists():
                        run_logged([str(isolated_pip), "install", "-e", str(pkg_path)], check=False)

    # Install local dev packages LAST (to override any versions from custom node requirements)
    console.print("Installing local dev packages (editable)...")
    utils_dir = UTILS_REPOS_DIR
    for pkg in ["comfy-env", "comfy-test", "comfy-3d-viewers", "comfy-attn"]:
        pkg_path = utils_dir / pkg
        if pkg_path.exists():
            run_logged(["uv", "pip", "install", "-e", str(pkg_path), "--python", str(env_python)])

    console.print()
    console.print(f"[green]Done![/green] Run with: [cyan]{COMMAND_NAME} start {env_name}[/cyan]")
    console.print(f"Or manually: [cyan]cd {comfyui_path} && \"{env_python}\" main.py[/cyan]")
    logger.info(f"Setup complete for {config_name}")
