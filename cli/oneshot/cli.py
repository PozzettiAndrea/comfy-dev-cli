#!/usr/bin/env python3
"""
oneshot: Tooling for one-shot ComfyUI wrapper implementations.

Commands:
    (no args)           - List available package configs
    setup <NAME>        - Create/resume a wrapper package from config
    assess              - AI feasibility analysis
    design              - Scope discussion → considerations.md
    workflows           - Generate workflow JSONs
    implement           - Fill cookiecutter template
    license             - License recommendation
    switch <NAME>       - Switch active config
    init <GITHUB_URL>   - Create wrapper folder with inputs.yml template
    pullall             - Fetch all resources listed in inputs.yml
"""

import json
import os
import subprocess
import typer
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .patterns import parse_github_url
from .extractors import (
    fetch_github_metadata,
    fetch_readme,
    download_paper_pdf,
    fetch_hf_model_files,
    convert_pdf_to_markdown,
    get_paper_cache_key,
    get_cached_paper_md,
    save_paper_to_cache,
)

# Paths
CLI_DIR = Path(__file__).parent.parent
ROOT_DIR = Path(os.environ["CDS_ROOT"]) if "CDS_ROOT" in os.environ else CLI_DIR.parent
ONESHOT_CONFIG_DIR = ROOT_DIR / "config" / "oneshot"
ONESHOTS_DIR = Path("/home/shadeform/oneshots")
ONESHOT_CACHE_DIR = ONESHOTS_DIR  # Use same directory for everything
ACTIVE_CONFIG_FILE = ONESHOTS_DIR / ".active"

console = Console()


def get_active_config() -> str | None:
    """Get the currently active config name."""
    if ACTIVE_CONFIG_FILE.exists():
        name = ACTIVE_CONFIG_FILE.read_text().strip()
        if name and load_oneshot_config(name):
            return name
    return None


def set_active_config(name: str):
    """Set the active config."""
    ONESHOT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_CONFIG_FILE.write_text(name)


def list_oneshot_configs():
    """List available oneshot package configs."""
    if not ONESHOT_CONFIG_DIR.exists():
        console.print("[yellow]No oneshot configs found.[/yellow]")
        console.print(f"[dim]Create configs in: {ONESHOT_CONFIG_DIR}[/dim]")
        return []

    configs = sorted([f.stem for f in ONESHOT_CONFIG_DIR.glob("*.yml")])
    if not configs:
        console.print("[yellow]No oneshot configs found.[/yellow]")
        console.print(f"[dim]Create configs in: {ONESHOT_CONFIG_DIR}[/dim]")
        return []

    return configs


def load_oneshot_config(name: str) -> dict | None:
    """Load a oneshot config by name."""
    config_file = ONESHOT_CONFIG_DIR / f"{name}.yml"
    if not config_file.exists():
        return None

    with open(config_file) as f:
        return yaml.safe_load(f)


def get_cached_package_dir(name: str, config: dict = None) -> Path:
    """Get the cached package directory for a config."""
    if config and config.get("package_name"):
        return ONESHOT_CACHE_DIR / config["package_name"]
    return ONESHOT_CACHE_DIR / f"wrapper_{name}"


def resolve_wrapper_dir(name: str = None, require_exists: bool = True) -> Path | None:
    """Resolve wrapper directory - prioritizes local wrapper over database."""
    # Always check for local wrapper first (primary location)
    local_wrapper = find_wrapper_dir()
    if local_wrapper:
        return local_wrapper

    # If no local wrapper, try to resolve from config name or active config
    if not name:
        name = get_active_config()
        if not name:
            if require_exists:
                console.print("[red]No wrapper directory found.[/red]")
                console.print("[dim]Run 'ct oneshot setup' from a wrapper directory.[/dim]")
            return None

    config = load_oneshot_config(name)
    if not config:
        console.print(f"[red]Config not found: {name}[/red]")
        return None

    # Fall back to database location
    wrapper_dir = get_cached_package_dir(name, config)
    if require_exists and not wrapper_dir.exists():
        console.print(f"[red]Package not found. Run 'ct oneshot setup' first.[/red]")
        return None

    return wrapper_dir


# Pipeline steps
PIPELINE_STEPS = [
    ("setup", "Setup", "Clone repo, download paper, fetch HF info"),
    ("assess", "Assess", "AI feasibility analysis"),
    ("design", "Design", "Scope discussion → considerations.md"),
    ("workflows", "Workflows", "Generate workflow JSONs + find assets"),
    ("implement", "Implement", "Fill cookiecutter template"),
    ("license", "License", "License recommendation"),
]


def get_pipeline_status(wrapper_dir: Path) -> dict:
    """Check which pipeline steps are complete."""
    status = {}
    checks = {
        "setup": lambda d: (d / "repo").exists() or (d / "inputs.yml").exists(),
        "assess": lambda d: (d / "initial-assessment.md").exists(),
        "design": lambda d: (d / "considerations.md").exists(),
        "workflows": lambda d: (d / "workflows").exists() and any((d / "workflows").glob("*.json")),
        "implement": lambda d: (d / "cookiecutter-fill.md").exists(),
        "license": lambda d: (d / "license-recommendation.md").exists(),
    }
    for step, _, _ in PIPELINE_STEPS:
        status[step] = checks.get(step, lambda d: False)(wrapper_dir)
    return status


def show_pipeline_status(wrapper_dir: Path, current_step: str = None):
    """Display pipeline progress bar."""
    status = get_pipeline_status(wrapper_dir)

    console.print()
    console.print(f"[bold]Pipeline:[/bold] {wrapper_dir.name}")

    parts = []
    for step, label, _ in PIPELINE_STEPS:
        if step == current_step:
            parts.append(f"[bold yellow]▶ {label}[/bold yellow]")
        elif status.get(step):
            parts.append(f"[green]✓ {label}[/green]")
        else:
            parts.append(f"[dim]○ {label}[/dim]")

    console.print(" → ".join(parts))
    console.print()


def save_to_wrapper(wrapper_dir: Path, filename: str, content: str):
    """Save file to wrapper directory (and backup to database if different)."""
    # Save to wrapper_dir (primary - should be local wrapper)
    main_path = wrapper_dir / filename
    main_path.write_text(content)
    console.print(f"[green]✓[/green] Saved {filename}")

    # Also backup to database if wrapper_dir is not the database
    if ONESHOT_CACHE_DIR not in wrapper_dir.parents and wrapper_dir.parent != ONESHOT_CACHE_DIR:
        # Find matching database dir from active config
        active = get_active_config()
        if active:
            config = load_oneshot_config(active)
            if config:
                db_dir = get_cached_package_dir(active, config)
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = db_dir / filename
                db_path.write_text(content)
                console.print(f"[dim]  └─ backed up to database[/dim]")


def show_available_packages():
    """Display available oneshot packages."""
    configs = list_oneshot_configs()
    if configs:
        console.print("[bold]Available oneshot packages:[/bold]")
        console.print()

        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Package", style="dim")
        table.add_column("GitHub", style="dim")
        table.add_column("Cached", style="green")

        for name in configs:
            config = load_oneshot_config(name)
            github = config.get("github", "") if config else ""
            package_name = config.get("package_name", f"wrapper_{name}") if config else f"wrapper_{name}"
            # Shorten github URL
            if github:
                github = github.replace("https://github.com/", "")
            cached_dir = get_cached_package_dir(name, config)
            cached = "Yes" if cached_dir.exists() else "-"
            table.add_row(name, package_name, github, cached)

        console.print(table)
        console.print()
        console.print("Usage: [green]ct oneshot <name>[/green]")


app = typer.Typer(
    name="oneshot",
    help="Tooling for one-shot ComfyUI wrapper implementations",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def oneshot_callback(ctx: typer.Context):
    """List packages or show active config status."""
    if ctx.invoked_subcommand is None:
        # Check for local wrapper first
        local_wrapper = find_wrapper_dir()
        active = get_active_config()

        if local_wrapper:
            # Show local wrapper status
            if active:
                console.print(f"[bold cyan]Active config:[/bold cyan] {active}")
            console.print(f"[bold]Wrapper:[/bold] {local_wrapper}")
            show_pipeline_status(local_wrapper)
            console.print("[dim]Commands: setup, assess, design, workflows, implement, license[/dim]")
        elif active:
            config = load_oneshot_config(active)
            wrapper_dir = get_cached_package_dir(active, config)
            if wrapper_dir.exists():
                console.print(f"[bold cyan]Active config:[/bold cyan] {active}")
                console.print(f"[dim]Database location: {wrapper_dir}[/dim]")
                show_pipeline_status(wrapper_dir)
                console.print("[dim]Commands: setup, assess, design, workflows, implement, license[/dim]")
            else:
                console.print(f"[bold cyan]Active config:[/bold cyan] {active} [yellow](not initialized)[/yellow]")
                console.print(f"[dim]Run: ct oneshot setup[/dim]")
        else:
            show_available_packages()
            console.print()
            console.print("[dim]Activate a config: ct oneshot switch <name>[/dim]")


@app.command()
def switch(
    name: str = typer.Argument(..., help="Config name to activate"),
):
    """Switch to a different package config."""
    config = load_oneshot_config(name)
    if not config:
        console.print(f"[red]Config not found: {name}[/red]")
        configs = list_oneshot_configs()
        if configs:
            console.print(f"[dim]Available: {', '.join(configs)}[/dim]")
        raise typer.Exit(1)

    set_active_config(name)
    console.print(f"[green]Switched to:[/green] {name}")

    wrapper_dir = get_cached_package_dir(name, config)
    if wrapper_dir.exists():
        show_pipeline_status(wrapper_dir)
    else:
        console.print(f"[yellow]Package not initialized.[/yellow]")
        console.print(f"[dim]Run: ct oneshot setup[/dim]")


def find_wrapper_dir():
    """Find package directory in oneshots directory (has inputs.yml)."""
    # Ensure oneshots directory exists
    ONESHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Look for directories with inputs.yml (indicates a wrapper package)
    wrapper_dirs = [d.parent for d in ONESHOTS_DIR.glob("*/inputs.yml")]
    if not wrapper_dirs:
        return None
    # Return most recently modified
    return max(wrapper_dirs, key=lambda p: p.stat().st_mtime)


def load_inputs(wrapper_dir):
    """Load inputs.yml from wrapper directory."""
    yml_path = wrapper_dir / "inputs.yml"
    if not yml_path.exists():
        return None

    with open(yml_path) as f:
        return yaml.safe_load(f)


def load_cookiecutter_template(wrapper_dir: Path):
    """Load key cookiecutter template files as a formatted string."""
    template_dir = wrapper_dir / "cookiecutter-template"
    slug_dir = template_dir / "{{cookiecutter.project_slug}}" / "custom-nodes-template"
    common_dir = template_dir / "{{cookiecutter.project_slug}}" / "common"

    files_to_read = [
        (template_dir / "cookiecutter.json", "cookiecutter.json"),
        (slug_dir / "__init__.py", "__init__.py"),
        (slug_dir / "src" / "{{cookiecutter.project_slug}}" / "nodes.py", "nodes.py"),
        (slug_dir / "README.md", "README.md"),
        (slug_dir / "install.py", "install.py"),
        (common_dir / "pyproject.toml", "pyproject.toml"),
    ]

    content = []
    for file_path, display_name in files_to_read:
        if file_path.exists():
            content.append(f"### {display_name}\n```\n{file_path.read_text()}\n```\n")

    return "\n".join(content) if content else "Template not found (run 'ct oneshot discussion' first)"


@app.command()
def init(
    github_url: str = typer.Argument(..., help="GitHub repo URL or owner/repo shorthand"),
):
    """Create a wrapper folder with inputs.yml template."""
    # Parse GitHub URL
    owner, repo = parse_github_url(github_url)
    if not owner or not repo:
        console.print(f"[red]Invalid GitHub URL: {github_url}[/red]")
        raise typer.Exit(1)

    full_url = f"https://github.com/{owner}/{repo}"

    # Create wrapper directory in oneshots
    ONESHOTS_DIR.mkdir(parents=True, exist_ok=True)
    wrapper_dir = ONESHOTS_DIR / f"wrapper_{repo}"
    if wrapper_dir.exists():
        console.print(f"[yellow]Directory already exists: {wrapper_dir}[/yellow]")
        raise typer.Exit(1)

    wrapper_dir.mkdir()

    # Create inputs.yml with github pre-filled
    yml_path = wrapper_dir / "inputs.yml"
    inputs = {
        "github": full_url,
        "website": "",
        "huggingface": "",
        "paper": "",
        "comfyui-repo-link": "",  # Your ComfyUI node repo URL (for cookiecutter fill)
    }
    with open(yml_path, 'w') as f:
        yaml.dump(inputs, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]Created {wrapper_dir.name}/[/green]")
    console.print(f"  └─ inputs.yml")
    console.print()
    console.print("[dim]Edit inputs.yml to add website, huggingface, and paper links.[/dim]")
    console.print("[dim]Then run 'oneshot pullall' to fetch everything.[/dim]")


def _backup_to_database(local_wrapper: Path, db_dir: Path):
    """Copy key files from local wrapper to database backup."""
    import shutil

    # Files to backup (skip large directories like repo/)
    files_to_backup = [
        "inputs.yml",
        "info.json",
        "paper.md",
        "paper.pdf",
        "initial-assessment.md",
        "CLAUDE.md",
        "considerations.md",
        "cookiecutter-fill.md",
        "license-recommendation.md",
        "discussion-prompt.md",
        "workflows-prompt.md",
    ]

    backed_up = []
    for filename in files_to_backup:
        src = local_wrapper / filename
        if src.exists():
            dst = db_dir / filename
            shutil.copy2(src, dst)
            backed_up.append(filename)

    # Backup hf_models/ directory
    hf_src = local_wrapper / "hf_models"
    if hf_src.exists():
        hf_dst = db_dir / "hf_models"
        if hf_dst.exists():
            shutil.rmtree(hf_dst)
        shutil.copytree(hf_src, hf_dst)
        backed_up.append("hf_models/")

    # Backup workflows/ directory
    wf_src = local_wrapper / "workflows"
    if wf_src.exists():
        wf_dst = db_dir / "workflows"
        if wf_dst.exists():
            shutil.rmtree(wf_dst)
        shutil.copytree(wf_src, wf_dst)
        backed_up.append("workflows/")

    if backed_up:
        console.print(f"[dim]Backed up to database: {', '.join(backed_up)}[/dim]")


def _run_setup(name: str, config: dict):
    """Internal setup logic - creates/resumes a wrapper package."""
    # Set as active config
    set_active_config(name)

    # Use package_name from config if specified, otherwise use config name
    package_name = config.get("package_name", f"wrapper_{name}")

    # Primary: local wrapper directory in oneshots dir
    local_wrapper = find_wrapper_dir()
    if not local_wrapper:
        # Create local wrapper in oneshots directory
        ONESHOTS_DIR.mkdir(parents=True, exist_ok=True)
        local_wrapper = ONESHOTS_DIR / package_name
        local_wrapper.mkdir(exist_ok=True)
        console.print(f"[green]Created wrapper:[/green] {local_wrapper}")
    else:
        console.print(f"[cyan]Using wrapper:[/cyan] {local_wrapper}")

    show_pipeline_status(local_wrapper, "setup")

    # Create/update inputs.yml from config
    inputs = {
        "github": config.get("github", ""),
        "website": config.get("website", ""),
        "huggingface": config.get("huggingface", ""),
        "paper": config.get("paper", ""),
        "comfyui-repo-link": config.get("comfyui-repo-link", ""),
    }

    # Write to local wrapper (primary)
    yml_path = local_wrapper / "inputs.yml"
    with open(yml_path, 'w') as f:
        yaml.dump(inputs, f, default_flow_style=False, sort_keys=False)

    console.print()

    # Run pullall on local wrapper
    _run_pullall(local_wrapper, inputs)


@app.command(name="setup")
def setup(
    name: str = typer.Argument(None, help="Package config name (uses active config if not provided)"),
):
    """Create/resume a wrapper package from a config file."""
    # If no name provided, use active config
    if not name:
        name = get_active_config()
        if not name:
            console.print("[red]No config specified and no active config set.[/red]")
            console.print("[dim]Usage: ct oneshot setup <name>[/dim]")
            console.print("[dim]Or set active config: ct oneshot switch <name>[/dim]")
            raise typer.Exit(1)

    # Load config
    config = load_oneshot_config(name)
    if not config:
        console.print(f"[red]Config not found: {name}[/red]")
        configs = list_oneshot_configs()
        if configs:
            console.print(f"[dim]Available: {', '.join(configs)}[/dim]")
        raise typer.Exit(1)

    _run_setup(name, config)


def _run_pullall(wrapper_dir: Path, inputs: dict):
    """Internal pullall logic - shared between pullall command and package command."""
    console.print(f"[bold]Pulling resources for {wrapper_dir.name}[/bold]")
    console.print()

    info = {
        "github_url": inputs.get("github", ""),
        "github_meta": {},
        "paper_url": inputs.get("paper", ""),
        "paper_downloaded": False,
        "website_url": inputs.get("website", ""),
        "huggingface_url": inputs.get("huggingface", ""),
        "huggingface_fetched": False,
    }

    # 1. Clone GitHub repo
    github_url = inputs.get("github", "").strip()
    if github_url:
        owner, repo = parse_github_url(github_url)
        if owner and repo:
            repo_dir = wrapper_dir / "repo"
            if repo_dir.exists():
                console.print(f"[yellow]○[/yellow] GitHub repo already cloned")
            else:
                console.print(f"[dim]Cloning {owner}/{repo}...[/dim]")
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", github_url, str(repo_dir)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    console.print(f"[green]✓[/green] Cloned GitHub repo to repo/")
                else:
                    console.print(f"[red]✗[/red] Failed to clone: {result.stderr.strip()}")

            # Fetch metadata
            meta = fetch_github_metadata(owner, repo)
            if "error" not in meta:
                info["github_meta"] = meta
    else:
        console.print(f"[yellow]○[/yellow] No GitHub URL specified")

    # 2. Download paper PDF and convert to markdown
    paper_url = inputs.get("paper", "").strip()
    if paper_url:
        pdf_path = wrapper_dir / "paper.pdf"
        md_path = wrapper_dir / "paper.md"

        # Check cache first
        cache_key = get_paper_cache_key(paper_url)
        cached_md = get_cached_paper_md(cache_key)

        if md_path.exists():
            console.print(f"[yellow]○[/yellow] Paper markdown already exists")
            info["paper_converted"] = True
        elif cached_md:
            # Use cached version
            import shutil
            shutil.copy(cached_md, md_path)
            console.print(f"[green]✓[/green] Loaded paper.md from cache ({cache_key})")
            info["paper_converted"] = True
            info["paper_cached"] = True
        else:
            # Need to download and convert
            if pdf_path.exists():
                console.print(f"[yellow]○[/yellow] Paper PDF already downloaded")
                info["paper_downloaded"] = True
            else:
                console.print(f"[dim]Downloading paper from {paper_url}...[/dim]")
                if download_paper_pdf(paper_url, pdf_path):
                    console.print(f"[green]✓[/green] Downloaded paper.pdf")
                    info["paper_downloaded"] = True
                else:
                    console.print(f"[red]✗[/red] Failed to download paper")

            # Convert PDF to markdown if PDF exists
            if pdf_path.exists():
                console.print(f"[dim]Converting paper to markdown...[/dim]")
                result = convert_pdf_to_markdown(pdf_path, md_path)
                if result is None:
                    console.print(f"[yellow]○[/yellow] marker-pdf not installed, skipping conversion")
                    console.print(f"    └─ [dim]pip install marker-pdf[/dim]")
                elif result:
                    console.print(f"[green]✓[/green] Converted to paper.md")
                    info["paper_converted"] = True
                    # Save to cache
                    save_paper_to_cache(cache_key, md_path.read_text())
                    console.print(f"[green]✓[/green] Cached paper.md as {cache_key}")
                else:
                    console.print(f"[red]✗[/red] Failed to convert paper")
    else:
        console.print(f"[dim]○[/dim] No paper URL specified")

    # 3. Fetch HuggingFace model info
    hf_url = inputs.get("huggingface", "").strip()
    if hf_url:
        hf_dir = wrapper_dir / "hf_models"
        hf_dir.mkdir(exist_ok=True)

        console.print(f"[dim]Fetching HuggingFace model info...[/dim]")
        model_info = fetch_hf_model_files(hf_url)
        if model_info:
            # Save to JSON file
            model_id_safe = model_info["model_id"].replace("/", "_")
            hf_json_path = hf_dir / f"{model_id_safe}.json"
            with open(hf_json_path, 'w') as f:
                json.dump(model_info, f, indent=2)

            console.print(f"[green]✓[/green] Fetched HF model info ({model_info['total_size_human']} total)")
            console.print(f"    └─ {len(model_info['files'])} files in {model_info['model_id']}")
            info["huggingface_fetched"] = True
        else:
            console.print(f"[red]✗[/red] Failed to fetch HuggingFace model info")
    else:
        console.print(f"[dim]○[/dim] No HuggingFace URL specified")

    # 4. Note website (just store in info, nothing to download)
    website_url = inputs.get("website", "").strip()
    if website_url:
        console.print(f"[green]✓[/green] Website: {website_url}")
    else:
        console.print(f"[dim]○[/dim] No website URL specified")

    # Save info.json
    info_path = wrapper_dir / "info.json"
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)

    console.print()
    console.print(f"[green]Done![/green] Saved metadata to info.json")
    console.print(f"[dim]Package location: {wrapper_dir}[/dim]")
    console.print()
    console.print(f"[dim]Next: ct oneshot assess[/dim]")


@app.command()
def pullall():
    """Fetch all resources listed in inputs.yml."""
    # Find wrapper directory
    wrapper_dir = find_wrapper_dir()
    if not wrapper_dir:
        console.print("[red]No wrapper_* directory found in current directory.[/red]")
        console.print("[dim]Run 'oneshot init <GITHUB_URL>' first.[/dim]")
        raise typer.Exit(1)

    # Load inputs
    inputs = load_inputs(wrapper_dir)
    if not inputs:
        console.print(f"[red]No inputs.yml found in {wrapper_dir}[/red]")
        raise typer.Exit(1)

    _run_pullall(wrapper_dir, inputs)


@app.command(name="assess")
def assess(
    name: str = typer.Argument(None, help="Package config name"),
):
    """Analyze project feasibility and suggest initial scope using Claude."""
    from .prompts import get_initial_assessment_prompt

    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot assess <name>[/dim]")
        raise typer.Exit(1)

    show_pipeline_status(wrapper_dir, "assess")

    # Build paths
    repo_path = wrapper_dir / "repo"
    paper_path = wrapper_dir / "paper.md"
    info_path = wrapper_dir / "info.json"
    hf_dir = wrapper_dir / "hf_models"

    # Find HF model JSON files
    hf_files = list(hf_dir.glob("*.json")) if hf_dir.exists() else []
    hf_path_str = ", ".join(str(f) for f in hf_files) if hf_files else "Not available"

    # Build prompt with paths (let Claude read them)
    prompt = get_initial_assessment_prompt().format(
        project_name=wrapper_dir.name,
        repo_path=repo_path if repo_path.exists() else "Not available",
        paper_path=paper_path if paper_path.exists() else "Not available",
        info_path=info_path if info_path.exists() else "Not available",
        hf_path=hf_path_str,
    )

    # Launch Claude interactively
    console.print("[green]▶[/green] Launching Claude for assessment...")
    console.print()
    subprocess.run(["claude", "--allowedTools", "WebSearch,WebFetch", "--", prompt], cwd=wrapper_dir)


@app.command(name="design")
def design(
    name: str = typer.Argument(None, help="Package config name"),
):
    """Scope discussion - outputs considerations.md."""
    from .prompts import get_discussion_prompt

    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot design <name>[/dim]")
        raise typer.Exit(1)

    show_pipeline_status(wrapper_dir, "design")

    # Check that assess was completed
    assessment_path = wrapper_dir / "initial-assessment.md"
    if not assessment_path.exists():
        console.print("[red]No initial-assessment.md found.[/red]")
        console.print("[dim]Run 'ct oneshot assess' first.[/dim]")
        raise typer.Exit(1)

    # Get discussion prompt
    prompt_content = get_discussion_prompt()
    save_to_wrapper(wrapper_dir, "design-prompt.md", prompt_content)

    # Launch Claude interactively
    console.print("[green]▶[/green] Launching Claude for design discussion...")
    console.print()
    subprocess.run(["claude", "--allowedTools", "WebSearch,WebFetch", "--", prompt_content], cwd=wrapper_dir)


@app.command()
def workflows(
    name: str = typer.Argument(None, help="Package config name"),
):
    """Generate workflow JSONs and find example assets."""
    from .prompts import get_workflows_prompt

    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot workflows <name>[/dim]")
        raise typer.Exit(1)

    show_pipeline_status(wrapper_dir, "workflows")

    # Check that design was completed
    considerations_path = wrapper_dir / "considerations.md"
    if not considerations_path.exists():
        console.print("[red]No considerations.md found.[/red]")
        console.print("[dim]Run 'ct oneshot design' first.[/dim]")
        raise typer.Exit(1)

    # Create workflows and assets directories
    for subdir in ["workflows", "assets"]:
        dir_path = wrapper_dir / subdir
        if not dir_path.exists():
            dir_path.mkdir()
            console.print(f"[green]✓[/green] Created {subdir}/")

    # Get prompt (uses relative paths, Claude reads from cwd)
    prompt_content = get_workflows_prompt()

    # Launch Claude with the prompt
    console.print("[green]▶[/green] Launching Claude for workflows design...")
    console.print()
    subprocess.run(["claude", "--allowedTools", "WebSearch,WebFetch", "--", prompt_content], cwd=wrapper_dir)


@app.command(hidden=True)
def considerations(
    name: str = typer.Argument(None, help="Package config name"),
):
    """[DEPRECATED] Old workflow - use 'discussion' instead."""
    from .prompts import get_considerations_prompt

    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot considerations <name>[/dim]")
        raise typer.Exit(1)

    # Check that feasibility-scope-revised.md exists
    scope_path = wrapper_dir / "feasibility-scope-revised.md"
    if not scope_path.exists():
        console.print("[red]No feasibility-scope-revised.md found.[/red]")
        console.print("[dim]Run 'oneshot discussion' and complete the Claude session first.[/dim]")
        raise typer.Exit(1)

    console.print(f"[bold]Generating considerations for {wrapper_dir.name}...[/bold]")
    console.print()

    # Gather context
    project_name = wrapper_dir.name.replace("wrapper_", "")

    # Read feasibility-scope-revised.md
    scope_content = scope_path.read_text()
    console.print(f"[green]✓[/green] Found feasibility-scope-revised.md ({len(scope_content)} chars)")

    # Read initial-assessment.md if exists
    assessment_content = ""
    assessment_path = wrapper_dir / "initial-assessment.md"
    if assessment_path.exists():
        assessment_content = assessment_path.read_text()
        console.print(f"[green]✓[/green] Found initial-assessment.md")

    # Read CLAUDE.md if exists
    claude_md_content = ""
    claude_path = wrapper_dir / "CLAUDE.md"
    if claude_path.exists():
        claude_md_content = claude_path.read_text()
        console.print(f"[green]✓[/green] Found CLAUDE.md")

    # Read repo README
    repo_readme = ""
    repo_dir = wrapper_dir / "repo"
    if repo_dir.exists():
        for readme_name in ["README.md", "readme.md", "README.rst", "README.txt"]:
            readme_path = repo_dir / readme_name
            if readme_path.exists():
                repo_readme = readme_path.read_text()[:10000]
                console.print(f"[green]✓[/green] Found repo README")
                break

    # Load cookiecutter template
    cookiecutter_template = load_cookiecutter_template(wrapper_dir)
    console.print(f"[green]✓[/green] Loaded cookiecutter template")

    # Build prompt
    prompt = get_considerations_prompt().format(
        project_name=project_name,
        scope_content=scope_content,
        assessment_content=assessment_content or "Not available",
        claude_md_content=claude_md_content or "Not available",
        repo_readme=repo_readme or "Not available",
        cookiecutter_template=cookiecutter_template,
    )

    console.print()
    console.print("[dim]Running Claude analysis (this may take 30-60 seconds)...[/dim]")

    # Call Claude via subprocess
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            console.print(f"[red]Claude error:[/red] {result.stderr}")
            raise typer.Exit(1)

        output = result.stdout

        # Save considerations.md
        save_to_wrapper(wrapper_dir, "considerations.md", output)

        # Print summary
        console.print()
        console.print("[bold]═══ Considerations ═══[/bold]")
        console.print()
        console.print(output[:2000])
        if len(output) > 2000:
            console.print()
            console.print(f"[dim]... (see full report in considerations.md)[/dim]")

        console.print()
        console.print("[dim]Next: Run 'oneshot fill' to generate the cookiecutter template.[/dim]")

    except subprocess.TimeoutExpired:
        console.print("[red]Claude analysis timed out after 5 minutes[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]'claude' command not found. Is Claude Code installed?[/red]")
        raise typer.Exit(1)


@app.command()
def implement(
    name: str = typer.Argument(None, help="Package config name"),
):
    """Fill cookiecutter template using Claude and gathered context."""
    from .prompts import get_fill_prompt

    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot implement <name>[/dim]")
        raise typer.Exit(1)

    show_pipeline_status(wrapper_dir, "implement")

    # Check that workflows exist
    workflows_dir = wrapper_dir / "workflows"
    if not workflows_dir.exists() or not any(workflows_dir.glob("*.json")):
        console.print("[red]No workflow JSONs found.[/red]")
        console.print("[dim]Run 'ct oneshot workflows' first.[/dim]")
        raise typer.Exit(1)

    # Get project info
    project_name = wrapper_dir.name.replace("wrapper_", "")

    # Load inputs.yml for comfyui-repo-link
    inputs = load_inputs(wrapper_dir) or {}
    comfyui_repo_link = inputs.get("comfyui-repo-link", "")

    # Build prompt with file paths (Claude will read them)
    prompt = get_fill_prompt().format(
        project_name=project_name,
        comfyui_repo_link=comfyui_repo_link or "Not specified",
    )

    # Launch Claude interactively
    console.print("[green]▶[/green] Launching Claude for implementation...")
    console.print()
    subprocess.run(["claude", "--allowedTools", "WebSearch,WebFetch", "--", prompt], cwd=wrapper_dir)


@app.command()
def license(
    name: str = typer.Argument(None, help="Package config name"),
):
    """Analyze original repo license and recommend a license for the wrapper."""
    wrapper_dir = resolve_wrapper_dir(name)
    if not wrapper_dir:
        if not name:
            console.print("[dim]Usage: ct oneshot license <name>[/dim]")
        raise typer.Exit(1)

    show_pipeline_status(wrapper_dir, "license")
    console.print(f"[bold]Analyzing license for {wrapper_dir.name}...[/bold]")
    console.print()

    project_name = wrapper_dir.name.replace("wrapper_", "")

    # Find original repo license
    repo_dir = wrapper_dir / "repo"
    original_license = ""
    license_file = None

    if repo_dir.exists():
        for license_name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
            license_path = repo_dir / license_name
            if license_path.exists():
                original_license = license_path.read_text()
                license_file = license_name
                break

    if original_license:
        console.print(f"[green]✓[/green] Found {license_file}")

        # Detect license type
        license_lower = original_license.lower()
        if "apache" in license_lower:
            detected = "Apache 2.0"
        elif "mit" in license_lower:
            detected = "MIT"
        elif "gpl" in license_lower and "lesser" in license_lower:
            detected = "LGPL"
        elif "gpl" in license_lower:
            detected = "GPL"
        elif "bsd" in license_lower:
            detected = "BSD"
        elif "cc0" in license_lower or "public domain" in license_lower:
            detected = "Public Domain / CC0"
        else:
            detected = "Unknown"

        console.print(f"[bold]Detected license:[/bold] {detected}")
        console.print()

        # Show compatibility table
        table = Table(title="License Compatibility for Your Wrapper")
        table.add_column("Original License", style="cyan")
        table.add_column("Compatible Wrapper Licenses", style="green")
        table.add_column("Recommendation", style="yellow")

        compatibility = {
            "MIT": ("MIT, Apache 2.0, GPL, LGPL", "MIT (keep it simple)"),
            "Apache 2.0": ("Apache 2.0, GPL v3", "Apache 2.0 (same as original)"),
            "GPL": ("GPL only (copyleft)", "GPL v3 (required by copyleft)"),
            "LGPL": ("LGPL, GPL", "LGPL (allows linking)"),
            "BSD": ("BSD, MIT, Apache 2.0, GPL", "MIT (most permissive)"),
            "Public Domain / CC0": ("Any license", "MIT (most common for ComfyUI nodes)"),
            "Unknown": ("Check original license carefully", "Ask original authors"),
        }

        compat = compatibility.get(detected, ("Unknown", "Check original"))
        table.add_row(detected, compat[0], compat[1])
        console.print(table)

        console.print()
        console.print("[bold]License file preview:[/bold]")
        console.print(original_license[:1000])
        if len(original_license) > 1000:
            console.print(f"[dim]... ({len(original_license)} chars total)[/dim]")

        # Save recommendation
        rec_content = f"""# License Recommendation for {project_name}

## Original License
- **Detected**: {detected}
- **File**: {license_file}

## Recommendation
{compat[1]}

## Compatible Options
{compat[0]}

## Original License Text
```
{original_license}
```
"""
        console.print()
        save_to_wrapper(wrapper_dir, "license-recommendation.md", rec_content)

    else:
        console.print("[yellow]○[/yellow] No LICENSE file found in repo/")
        console.print("[dim]Check the original repository for license information.[/dim]")


if __name__ == "__main__":
    app()
