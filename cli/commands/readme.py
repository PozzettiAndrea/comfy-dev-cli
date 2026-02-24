"""Browse full GitHub repo pages for all managed repos via local proxy."""

import os
import re

import httpx
from rich.console import Console

from config import get_all_repos, GITHUB_OWNER


def serve_readmes(port: int = 8002, threshold: int = 0):
    """Launch a browse UI that proxies full GitHub repo pages."""
    import signal
    import sys
    import webbrowser

    import uvicorn
    from fastapi import FastAPI
    from fastapi.requests import Request
    from fastapi.responses import HTMLResponse, Response
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    console = Console()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]GITHUB_TOKEN not set.[/red]")
        raise SystemExit(1)

    repos = get_all_repos()
    if threshold > 0:
        repos = [r for r in repos if r.stars >= threshold]
    repo_names = sorted([r.name for r in repos], key=str.lower)

    if not repo_names:
        console.print("[yellow]No repos found.[/yellow]")
        return

    console.print(f"[green]Loaded {len(repo_names)} repos[/green]")

    client = httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        },
    )

    browse_app = FastAPI()
    templates_dir = Path(__file__).parent.parent / "dashboard" / "templates"
    templates = Jinja2Templates(directory=templates_dir)

    @browse_app.get("/", response_class=HTMLResponse)
    async def browse_root(request: Request):
        return templates.TemplateResponse("readme_browse.html", {
            "request": request,
            "repo_names": repo_names,
            "github_owner": GITHUB_OWNER,
        })

    @browse_app.get("/proxy/{repo_name:path}", response_class=HTMLResponse)
    async def proxy_github(repo_name: str):
        """Proxy a GitHub repo page, stripping frame-blocking headers."""
        # Only allow proxying repos we manage
        base_repo = repo_name.split("/")[0]
        if base_repo not in repo_names:
            return HTMLResponse("<h1>Not found</h1>", status_code=404)

        url = f"https://github.com/{GITHUB_OWNER}/{repo_name}"
        try:
            resp = await client.get(url)
        except Exception as e:
            return HTMLResponse(f"<h1>Error fetching page</h1><p>{e}</p>", status_code=502)

        if resp.status_code != 200:
            return HTMLResponse(f"<h1>{resp.status_code}</h1>", status_code=resp.status_code)

        html = resp.text

        # Rewrite relative URLs to go through our proxy or to absolute GitHub URLs
        html = html.replace('href="/', f'href="https://github.com/')
        html = html.replace("href='/", f"href='https://github.com/")
        html = html.replace('src="/', f'src="https://github.com/')
        html = html.replace("src='/", f"src='https://github.com/")
        html = html.replace('action="/', f'action="https://github.com/')

        # Return without X-Frame-Options / CSP so iframe works
        return HTMLResponse(html)

    @browse_app.on_event("shutdown")
    async def shutdown():
        await client.aclose()

    def _shutdown(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    console.print(f"[bold green]Serving repo browser at http://localhost:{port}[/bold green]")
    console.print(f"[dim]Press Ctrl+C to stop[/dim]")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(browse_app, host="0.0.0.0", port=port, log_level="warning")
