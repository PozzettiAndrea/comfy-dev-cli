"""Audit licenses across all repos."""

import os
import subprocess
import tempfile
import concurrent.futures
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import GITHUB_OWNER

console = Console()

# DeepSeek model on OpenRouter - good balance of cost/quality
OPENROUTER_MODEL = "deepseek/deepseek-chat"

DEEP_ANALYSIS_PROMPT = '''You are a software license compliance expert. Analyze this repository's license situation.

## Repository: {repo_name}

## Files Found:
{file_tree}

## LICENSE file content (root):
{license_content}

## Other license files found:
{other_licenses}

## README license section:
{readme_license_section}

## Vendor/third-party directories:
{vendor_dirs}

---

Provide a concise analysis covering:

1. **Main License**: What license covers the wrapper/main code?
2. **Vendored Code**: List any vendored/third-party code and their licenses
3. **Compatibility Issues**: Any license conflicts? (e.g., GPL wrapper around non-commercial code)
4. **Missing Info**: Is it clear what the license covers? Any ambiguity?
5. **Recommendations**: Specific actionable fixes needed (if any)

Use this format:
- Status: OK | NEEDS_ATTENTION | CRITICAL
- Main License: <license>
- Issues: <bullet list or "None">
- Action Items: <bullet list or "None">

Be concise. Focus on actionable issues only.'''


def audit_licenses(repo_name: str | None):
    """Audit licenses for managed repos."""
    from github import Github
    from config import get_all_repos, get_github_token, GITHUB_OWNER

    token = get_github_token()
    if not token:
        console.print("[red]GITHUB_TOKEN environment variable not set.[/red]")
        return

    g = Github(token)
    repos = get_all_repos()

    if repo_name:
        repos = [r for r in repos if r.name == repo_name]

    table = Table(title="License Audit")
    table.add_column("Repo", style="cyan")
    table.add_column("License", style="yellow")
    table.add_column("SPDX ID", style="green")
    table.add_column("Status", style="bold")

    results = []

    with console.status("[bold green]Checking licenses..."):
        for repo in repos:
            try:
                gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo.name}")
                license_info = gh_repo.get_license()

                if license_info and license_info.license:
                    lic = license_info.license
                    results.append({
                        "repo": repo.name,
                        "name": lic.name,
                        "spdx_id": lic.spdx_id,
                        "status": "OK",
                        "status_style": "green",
                    })
                else:
                    results.append({
                        "repo": repo.name,
                        "name": "None",
                        "spdx_id": "-",
                        "status": "Missing",
                        "status_style": "red",
                    })

            except Exception as e:
                results.append({
                    "repo": repo.name,
                    "name": "Unknown",
                    "spdx_id": "-",
                    "status": "Error",
                    "status_style": "yellow",
                })

    # Sort: missing first, then by license name
    results.sort(key=lambda x: (x["status"] != "Missing", x["name"]))

    for r in results:
        table.add_row(
            r["repo"],
            r["name"],
            r["spdx_id"],
            f"[{r['status_style']}]{r['status']}[/{r['status_style']}]",
        )

    console.print(table)

    # Summary
    license_counts = {}
    missing = 0
    for r in results:
        if r["status"] == "Missing":
            missing += 1
        else:
            name = r["name"]
            license_counts[name] = license_counts.get(name, 0) + 1

    console.print("\n[bold]Summary:[/bold]")
    for name, count in sorted(license_counts.items(), key=lambda x: -x[1]):
        console.print(f"  {name}: {count}")
    if missing:
        console.print(f"  [red]Missing: {missing}[/red]")


def _get_openrouter_token():
    """Get OpenRouter API token from env or prompt user."""
    token = os.environ.get("OPENROUTER_API_KEY")
    if token:
        return token

    console.print("\n[yellow]OpenRouter API key not found in environment.[/yellow]")
    console.print("Get your API key at: https://openrouter.ai/keys")
    console.print("Using model: [cyan]deepseek/deepseek-chat[/cyan] (~$0.15/M input tokens)\n")

    import getpass
    token = getpass.getpass("Enter your OpenRouter API key: ")
    if not token.strip():
        console.print("[red]No API key provided. Exiting.[/red]")
        return None
    return token.strip()


def _clone_repo(repo_url: str, target_dir: Path) -> bool:
    """Clone a repo to target directory."""
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _scan_repo_licenses(repo_dir: Path) -> dict:
    """Scan a repo for license-related files and info."""
    result = {
        "file_tree": "",
        "license_content": "No LICENSE file found",
        "other_licenses": [],
        "readme_license_section": "No license section found in README",
        "vendor_dirs": [],
    }

    # Get top-level file tree
    files = []
    for item in sorted(repo_dir.iterdir()):
        if item.name.startswith(".git"):
            continue
        prefix = "📁 " if item.is_dir() else "📄 "
        files.append(f"{prefix}{item.name}")
    result["file_tree"] = "\n".join(files[:30])  # Limit to 30 items

    # Read root LICENSE file
    license_file = repo_dir / "LICENSE"
    if not license_file.exists():
        license_file = repo_dir / "LICENSE.md"
    if not license_file.exists():
        license_file = repo_dir / "LICENSE.txt"

    if license_file.exists():
        content = license_file.read_text(errors="ignore")
        # Truncate if too long, keep header
        if len(content) > 2000:
            content = content[:2000] + "\n... (truncated)"
        result["license_content"] = content

    # Find other license files
    for license_path in repo_dir.rglob("*LICENSE*"):
        if license_path == license_file:
            continue
        if ".git" in str(license_path):
            continue
        rel_path = license_path.relative_to(repo_dir)
        try:
            content = license_path.read_text(errors="ignore")[:500]
            result["other_licenses"].append(f"### {rel_path}\n{content}...")
        except:
            result["other_licenses"].append(f"### {rel_path}\n(could not read)")

    result["other_licenses"] = "\n\n".join(result["other_licenses"]) or "None found"

    # Extract license section from README
    readme_file = repo_dir / "README.md"
    if readme_file.exists():
        readme_content = readme_file.read_text(errors="ignore")
        # Find license section
        import re
        match = re.search(
            r'(?:^|\n)(#{1,3}\s*(?:License|Licensing).*?)(?=\n#{1,3}\s|\Z)',
            readme_content,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            section = match.group(1).strip()
            if len(section) > 1000:
                section = section[:1000] + "..."
            result["readme_license_section"] = section

    # Find vendor/third-party directories
    vendor_patterns = ["vendor", "third_party", "external", "lib", "deps"]
    for pattern in vendor_patterns:
        for vendor_path in repo_dir.glob(f"*{pattern}*"):
            if vendor_path.is_dir() and ".git" not in str(vendor_path):
                # List contents
                contents = [f.name for f in sorted(vendor_path.iterdir())[:10]]
                result["vendor_dirs"].append(f"- {vendor_path.name}/: {', '.join(contents)}")

    # Also check for common vendored code patterns (directories with __init__.py that aren't nodes/)
    for py_dir in repo_dir.iterdir():
        if py_dir.is_dir() and (py_dir / "__init__.py").exists():
            if py_dir.name not in ["nodes", "tests", "utils", "web", "docs", "assets"]:
                if py_dir.name not in [v.split("/")[0].replace("- ", "") for v in result["vendor_dirs"]]:
                    result["vendor_dirs"].append(f"- {py_dir.name}/ (potential vendored code)")

    result["vendor_dirs"] = "\n".join(result["vendor_dirs"]) or "None detected"

    return result


def _call_openrouter(prompt: str, api_key: str) -> str:
    """Call OpenRouter API with the given prompt."""
    import urllib.request
    import json

    data = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": f"https://github.com/{GITHUB_OWNER}/coding-scripts",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling API: {e}"


def _analyze_single_repo(repo, api_key: str, work_dir: Path) -> dict:
    """Analyze a single repo and return results."""
    from config import GITHUB_OWNER

    repo_dir = work_dir / repo.name
    repo_url = f"https://github.com/{GITHUB_OWNER}/{repo.name}.git"

    # Clone
    if not _clone_repo(repo_url, repo_dir):
        return {"repo": repo.name, "status": "ERROR", "analysis": "Failed to clone"}

    # Scan
    scan_data = _scan_repo_licenses(repo_dir)

    # Build prompt
    prompt = DEEP_ANALYSIS_PROMPT.format(
        repo_name=repo.name,
        file_tree=scan_data["file_tree"],
        license_content=scan_data["license_content"],
        other_licenses=scan_data["other_licenses"],
        readme_license_section=scan_data["readme_license_section"],
        vendor_dirs=scan_data["vendor_dirs"],
    )

    # Call AI
    analysis = _call_openrouter(prompt, api_key)

    # Extract status from response (handle various formats)
    # Look for "Status: X" pattern more carefully
    import re
    status = "UNKNOWN"
    status_match = re.search(r'status[:\s*]+\*{0,2}(OK|NEEDS_ATTENTION|CRITICAL)', analysis, re.IGNORECASE)
    if status_match:
        status = status_match.group(1).upper()

    return {"repo": repo.name, "status": status, "analysis": analysis}


def deep_audit_licenses(repo_name: str | None):
    """Deep AI-powered license analysis."""
    from config import get_all_repos

    # Get API key
    api_key = _get_openrouter_token()
    if not api_key:
        return

    repos = get_all_repos()
    if repo_name:
        repos = [r for r in repos if r.name == repo_name]

    if not repos:
        console.print("[red]No repos found.[/red]")
        return

    console.print(f"\n[bold]Deep License Analysis[/bold] - {len(repos)} repos")
    console.print(f"Model: [cyan]{OPENROUTER_MODEL}[/cyan]\n")

    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Process repos (could parallelize, but being nice to API)
            for repo in repos:
                task = progress.add_task(f"Analyzing {repo.name}...", total=None)
                result = _analyze_single_repo(repo, api_key, work_dir)
                results.append(result)
                progress.remove_task(task)

                # Show result immediately
                status_color = {
                    "OK": "green",
                    "NEEDS_ATTENTION": "yellow",
                    "CRITICAL": "red",
                    "ERROR": "red",
                    "UNKNOWN": "dim",
                }.get(result["status"], "white")

                console.print(Panel(
                    Markdown(result["analysis"]),
                    title=f"[{status_color}]{repo.name}[/{status_color}] - {result['status']}",
                    border_style=status_color,
                ))
                console.print()

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    for status, count in sorted(status_counts.items()):
        color = {"OK": "green", "NEEDS_ATTENTION": "yellow", "CRITICAL": "red"}.get(status, "white")
        console.print(f"  [{color}]{status}: {count}[/{color}]")
