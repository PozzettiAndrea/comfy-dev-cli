"""List GitHub Pages sites deployed from gh-pages branches."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from rich.console import Console
from rich.table import Table

from config import get_all_repos, GITHUB_OWNER


def _check_pages(repo_name: str, token: str) -> dict | None:
    """Check if a repo has GitHub Pages enabled. Returns info dict or None."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # Check the GitHub Pages API endpoint
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo_name}/pages",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": repo_name,
                "url": data.get("html_url", f"https://{GITHUB_OWNER}.github.io/{repo_name}/"),
                "status": data.get("status", "unknown"),
                "branch": data.get("source", {}).get("branch", "gh-pages"),
                "path": data.get("source", {}).get("path", "/"),
                "https_enforced": data.get("https_enforced", False),
                "custom_domain": data.get("cname") or None,
            }
    except Exception:
        pass

    return None


def get_all_pages(token: str, repos: list, workers: int = 8) -> list[dict]:
    """Fetch all pages sites. Used by the dashboard and the serve command."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_check_pages, repo.name, token): repo
            for repo in repos
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    results.sort(key=lambda s: s["name"].lower())
    return results


def serve_pages(port: int = 8001):
    """Fetch pages data and launch the browse UI on a local port."""
    import signal
    import sys
    import webbrowser

    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    console = Console()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]GITHUB_TOKEN not set.[/red]")
        raise SystemExit(1)

    repos = get_all_repos()

    with console.status(f"[bold blue]Checking {len(repos)} repos for GitHub Pages..."):
        pages_sites = get_all_pages(token, repos)

    if not pages_sites:
        console.print("[yellow]No repos with GitHub Pages found.[/yellow]")
        return

    console.print(f"[green]Found {len(pages_sites)} sites[/green]")

    # Build a minimal FastAPI app just for the browse view
    browse_app = FastAPI()
    templates_dir = Path(__file__).parent.parent / "dashboard" / "templates"
    templates = Jinja2Templates(directory=templates_dir)

    @browse_app.get("/", response_class=HTMLResponse)
    async def browse_root(request: Request):
        return templates.TemplateResponse("pages_browse.html", {
            "request": request,
            "pages_sites": pages_sites,
            "github_owner": GITHUB_OWNER,
        })

    def _shutdown(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    console.print(f"[bold green]Serving pages browser at http://localhost:{port}[/bold green]")
    console.print(f"[dim]Press Ctrl+C to stop[/dim]")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(browse_app, host="0.0.0.0", port=port, log_level="warning")
