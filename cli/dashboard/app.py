"""FastAPI web dashboard for repo-tools."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_all_repos, refresh_repo_data, refresh_repo_stats, get_repo_stats, GITHUB_OWNER

app = FastAPI(title="repo-tools Dashboard")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Dashboard home page."""
    repos = get_all_repos()
    repo_stats = get_repo_stats()

    # Define special repo groups
    COMFYUI_UTILITIES = {"comfy-env", "comfy-test", "ComfyUI-3D_nodes_index", "cuda-wheels", "cookiecutter-comfy-extension", "comfy-3d-viewers", "comfy-dynamic-widgets", "ComfyUI-validate-endpoint"}
    MISC_GEOMETRY = {"OCCT-RT", "occt-rt-python", "occt-diff", "PyMesh"}

    # Split repos into categories
    comfyui_utilities = [r for r in repos if r.name in COMFYUI_UTILITIES]
    misc_geometry = [r for r in repos if r.name in MISC_GEOMETRY]
    private_repos = [r for r in repos if r.is_private]
    public_repos = [r for r in repos if not r.is_private and r.name not in COMFYUI_UTILITIES and r.name not in MISC_GEOMETRY]

    # Helper to calculate stats for a group
    def calc_stats(repo_list):
        return {
            "stars": sum(r.stars for r in repo_list),
            "issues": sum(r.open_issues for r in repo_list),
            "discussions": sum(repo_stats.get(r.name, {}).get("discussions", 0) for r in repo_list),
            "unanswered": sum(repo_stats.get(r.name, {}).get("unanswered", 0) for r in repo_list),
            "waiting": sum(repo_stats.get(r.name, {}).get("waiting_on_op", 0) for r in repo_list),
        }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "public_repos": public_repos,
        "comfyui_utilities": comfyui_utilities,
        "misc_geometry": misc_geometry,
        "private_repos": private_repos,
        "repo_stats": repo_stats,
        "public_stats": calc_stats(public_repos),
        "utilities_stats": calc_stats(comfyui_utilities),
        "geometry_stats": calc_stats(misc_geometry),
        "private_stats": calc_stats(private_repos),
    })


@app.get("/repos", response_class=HTMLResponse)
async def repos_page(request: Request):
    """Repos list page."""
    repos = get_all_repos()
    return templates.TemplateResponse("repos.html", {
        "request": request,
        "repos": sorted(repos, key=lambda r: r.stars, reverse=True),
    })


@app.get("/repos/{repo_name}/forks", response_class=HTMLResponse)
async def active_forks_page(request: Request, repo_name: str):
    """Show active forks for a specific repo."""
    repos = get_all_repos()
    repo = next((r for r in repos if r.name == repo_name), None)
    repo_stats = get_repo_stats()
    stats = repo_stats.get(repo_name, {})
    active_forks = stats.get("active_forks_list", [])

    # Sort by commits ahead (most active first)
    active_forks = sorted(active_forks, key=lambda f: f["ahead_by"], reverse=True)

    return templates.TemplateResponse("forks.html", {
        "request": request,
        "repo": repo,
        "repo_name": repo_name,
        "active_forks": active_forks,
    })


@app.get("/repos/{repo_name}/issues", response_class=HTMLResponse)
async def issues_page(request: Request, repo_name: str):
    """Show issues for a specific repo."""
    repos = get_all_repos()
    repo = next((r for r in repos if r.name == repo_name), None)
    repo_stats = get_repo_stats()
    stats = repo_stats.get(repo_name, {})
    issues = stats.get("issues_list", [])

    # Sort: waiting on OP first, then by date
    issues = sorted(issues, key=lambda i: (not i["waiting_on_op"], i["created"]))

    return templates.TemplateResponse("issues.html", {
        "request": request,
        "repo": repo,
        "repo_name": repo_name,
        "issues": issues,
        "waiting_count": sum(1 for i in issues if i["waiting_on_op"]),
    })


@app.get("/repos/{repo_name}/discussions", response_class=HTMLResponse)
async def discussions_page(request: Request, repo_name: str):
    """Show discussions for a specific repo."""
    repos = get_all_repos()
    repo = next((r for r in repos if r.name == repo_name), None)
    repo_stats = get_repo_stats()
    stats = repo_stats.get(repo_name, {})
    discussions = stats.get("discussions_list", [])

    # Sort: unanswered first, then by date
    discussions = sorted(discussions, key=lambda d: (not d["unanswered"], d["created"]))

    return templates.TemplateResponse("discussions.html", {
        "request": request,
        "repo": repo,
        "repo_name": repo_name,
        "discussions": discussions,
        "unanswered_count": sum(1 for d in discussions if d["unanswered"]),
    })


def load_issue_analysis() -> dict:
    """Load issue analysis data from folder structure."""
    from pathlib import Path
    import json

    analysis_dir = Path(__file__).parent.parent.parent / "command-center" / "issue_analysis"
    meta_file = analysis_dir / "_meta.json"

    if not analysis_dir.exists():
        return {"last_run": None, "analyses": {}}

    # Load metadata
    meta = {"last_run": None}
    if meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)

    # Load per-repo files
    analyses = {}
    for repo_file in analysis_dir.glob("*.json"):
        if repo_file.name.startswith("_"):
            continue
        repo_name = repo_file.stem
        with open(repo_file) as f:
            analyses[repo_name] = json.load(f)

    return {"last_run": meta.get("last_run"), "analyses": analyses}


def get_analysis_stats(analyses: dict, repo_stats: dict) -> dict:
    """Calculate stats for issue analysis overview."""
    total_analyzed = 0
    total_new = 0
    by_confidence = {"high": 0, "medium": 0, "low": 0}
    by_effort = {"quick-fix": 0, "moderate": 0, "major-refactor": 0}

    for repo_name, repo_data in analyses.items():
        for issue in repo_data.get("issues", []):
            total_analyzed += 1
            analysis = issue.get("analysis", {})
            conf = analysis.get("confidence", "medium")
            effort = analysis.get("effort", "moderate")
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
            by_effort[effort] = by_effort.get(effort, 0) + 1

    # Count unanalyzed issues
    for repo_name, stats in repo_stats.items():
        open_issues = len(stats.get("issues_list", []))
        analyzed_issues = len(analyses.get(repo_name, {}).get("issues", []))
        total_new += max(0, open_issues - analyzed_issues)

    return {
        "total_analyzed": total_analyzed,
        "total_new": total_new,
        "by_confidence": by_confidence,
        "by_effort": by_effort,
    }


@app.get("/issue-analysis", response_class=HTMLResponse)
async def issue_analysis_overview(request: Request):
    """Level 1: Repos overview with analyzed/new issue counts."""
    repos = get_all_repos()
    repo_stats = get_repo_stats()
    analysis_data = load_issue_analysis()
    analyses = analysis_data.get("analyses", {})

    # Build repo list with analysis stats
    repo_analysis = []
    for repo in repos:
        stats = repo_stats.get(repo.name, {})
        open_issues = stats.get("issues_list", [])
        analyzed = analyses.get(repo.name, {}).get("issues", [])
        analyzed_nums = {i["number"] for i in analyzed}

        # Check for stale analyses (new comments since analysis)
        stale_count = 0
        for issue in analyzed:
            current_comments = next(
                (i["comments"] for i in open_issues if i["number"] == issue["number"]),
                issue.get("comments_at_analysis", 0)
            )
            if current_comments > issue.get("comments_at_analysis", 0):
                stale_count += 1

        new_count = sum(1 for i in open_issues if i["number"] not in analyzed_nums)

        if len(open_issues) > 0 or len(analyzed) > 0:
            repo_analysis.append({
                "name": repo.name,
                "stars": repo.stars,
                "analyzed_count": len(analyzed),
                "new_count": new_count,
                "stale_count": stale_count,
                "total_open": len(open_issues),
            })

    # Sort by new issues first, then by name
    repo_analysis.sort(key=lambda r: (-r["new_count"], -r["stale_count"], r["name"]))

    stats = get_analysis_stats(analyses, repo_stats)

    return templates.TemplateResponse("issue_analysis.html", {
        "request": request,
        "repos": repo_analysis,
        "last_run": analysis_data.get("last_run"),
        "stats": stats,
    })


@app.get("/issue-analysis/{repo_name}", response_class=HTMLResponse)
async def issue_analysis_repo(request: Request, repo_name: str, sort: str = "actionability"):
    """Level 2: Issues list for a specific repo."""
    repos = get_all_repos()
    repo = next((r for r in repos if r.name == repo_name), None)
    repo_stats = get_repo_stats()
    stats = repo_stats.get(repo_name, {})
    open_issues = stats.get("issues_list", [])

    analysis_data = load_issue_analysis()
    analyzed = analysis_data.get("analyses", {}).get(repo_name, {}).get("issues", [])

    # Enrich analyzed issues with staleness info
    for issue in analyzed:
        current_comments = next(
            (i["comments"] for i in open_issues if i["number"] == issue["number"]),
            issue.get("comments_at_analysis", 0)
        )
        issue["is_stale"] = current_comments > issue.get("comments_at_analysis", 0)

        # Calculate actionability score (lower = more actionable)
        analysis = issue.get("analysis", {})
        effort_score = {"quick-fix": 1, "moderate": 2, "major-refactor": 3}.get(analysis.get("effort", "moderate"), 2)
        conf_score = {"high": 1, "medium": 2, "low": 3}.get(analysis.get("confidence", "medium"), 2)
        risk_score = {"low": 1, "medium": 2, "high": 3}.get(analysis.get("risk_of_regression", "medium"), 2)
        issue["actionability_score"] = effort_score + conf_score + risk_score

    # Sort based on parameter
    if sort == "effort":
        sort_key = lambda i: ({"quick-fix": 1, "moderate": 2, "major-refactor": 3}.get(i.get("analysis", {}).get("effort", "moderate"), 2), i["number"])
    elif sort == "confidence":
        sort_key = lambda i: ({"high": 1, "medium": 2, "low": 3}.get(i.get("analysis", {}).get("confidence", "medium"), 2), i["number"])
    elif sort == "risk":
        sort_key = lambda i: ({"low": 1, "medium": 2, "high": 3}.get(i.get("analysis", {}).get("risk_of_regression", "medium"), 2), i["number"])
    else:  # actionability (default)
        sort_key = lambda i: (i.get("actionability_score", 99), i["number"])

    analyzed.sort(key=sort_key)

    # Find unanalyzed issues
    analyzed_nums = {i["number"] for i in analyzed}
    unanalyzed = [i for i in open_issues if i["number"] not in analyzed_nums]

    return templates.TemplateResponse("issue_analysis_repo.html", {
        "request": request,
        "repo": repo,
        "repo_name": repo_name,
        "analyzed": analyzed,
        "unanalyzed": unanalyzed,
        "current_sort": sort,
    })


@app.get("/issue-analysis/{repo_name}/{issue_number}", response_class=HTMLResponse)
async def issue_analysis_detail(request: Request, repo_name: str, issue_number: int):
    """Level 3: Detailed view of a single issue analysis."""
    repos = get_all_repos()
    repo = next((r for r in repos if r.name == repo_name), None)

    analysis_data = load_issue_analysis()
    analyzed = analysis_data.get("analyses", {}).get(repo_name, {}).get("issues", [])
    issue = next((i for i in analyzed if i["number"] == issue_number), None)

    if not issue:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"/issue-analysis/{repo_name}")

    # Check staleness
    repo_stats = get_repo_stats()
    stats = repo_stats.get(repo_name, {})
    open_issues = stats.get("issues_list", [])
    current_comments = next(
        (i["comments"] for i in open_issues if i["number"] == issue_number),
        issue.get("comments_at_analysis", 0)
    )
    issue["is_stale"] = current_comments > issue.get("comments_at_analysis", 0)

    # Build copyable context for Claude Code
    analysis = issue.get("analysis", {})
    claude_context = f"""Fix issue #{issue_number} in {repo_name}: "{issue['title']}"

## Analysis Summary
{analysis.get('summary', 'No summary available')}

## Probable Cause (Confidence: {analysis.get('confidence', 'unknown')})
{analysis.get('probable_cause', 'Unknown')}

## Uncertainty Notes
{analysis.get('uncertainty_notes', 'None')}

## Suggested Fix
{analysis.get('suggested_fix', 'Unknown')}

## Related Files
{chr(10).join('- ' + f for f in analysis.get('related_files', [])) or 'None identified'}

## Original Issue
{issue['url']}
"""

    return templates.TemplateResponse("issue_analysis_detail.html", {
        "request": request,
        "repo": repo,
        "repo_name": repo_name,
        "issue": issue,
        "claude_context": claude_context,
    })


@app.post("/issue-analysis/{repo_name}/{issue_number}/status")
async def update_issue_status(repo_name: str, issue_number: int, request: Request):
    """Update the status of an analyzed issue."""
    import json
    from pathlib import Path
    from fastapi.responses import RedirectResponse

    form = await request.form()
    new_status = form.get("status", "new")

    repo_file = Path(__file__).parent.parent.parent / "command-center" / "issue_analysis" / f"{repo_name}.json"
    if not repo_file.exists():
        return RedirectResponse(url=f"/issue-analysis/{repo_name}/{issue_number}", status_code=303)

    with open(repo_file) as f:
        data = json.load(f)

    # Update status
    for issue in data.get("issues", []):
        if issue["number"] == issue_number:
            issue["status"] = new_status
            break

    with open(repo_file, "w") as f:
        json.dump(data, f, indent=2)

    return RedirectResponse(url=f"/issue-analysis/{repo_name}/{issue_number}", status_code=303)


@app.get("/pages", response_class=HTMLResponse)
async def pages_overview(request: Request):
    """List all GitHub Pages sites."""
    import os
    from commands.pages import get_all_pages

    token = os.environ.get("GITHUB_TOKEN", "")
    repos = get_all_repos()
    pages_sites = get_all_pages(token, repos)

    return templates.TemplateResponse("pages.html", {
        "request": request,
        "pages_sites": pages_sites,
        "total_repos": len(repos),
        "github_owner": GITHUB_OWNER,
    })


@app.get("/pages/browse", response_class=HTMLResponse)
async def pages_browse(request: Request):
    """Browse GitHub Pages sites in an iframe viewer."""
    import os
    from commands.pages import get_all_pages

    token = os.environ.get("GITHUB_TOKEN", "")
    repos = get_all_repos()
    pages_sites = get_all_pages(token, repos)

    return templates.TemplateResponse("pages_browse.html", {
        "request": request,
        "pages_sites": pages_sites,
        "github_owner": GITHUB_OWNER,
    })


def run_dashboard(port: int = 8000):
    """Run the dashboard server."""
    import uvicorn
    from rich.console import Console

    console = Console()

    # Refresh repo data from GitHub before starting
    with console.status("[bold blue]Refreshing repo data from GitHub..."):
        if not refresh_repo_data():
            console.print("[red]Error: GITHUB_TOKEN not set. Cannot start dashboard.[/red]")
            console.print("Set it with: export GITHUB_TOKEN='your_token'")
            raise SystemExit(1)
        console.print("[green]Repo data refreshed[/green]")

    # Fetch discussion/issue stats (threaded for speed)
    console.print("[blue]Fetching repo stats (8 threads)...[/blue]")
    refresh_repo_stats(workers=8)
    console.print("[green]Repo stats refreshed[/green]")

    console.print(f"[bold green]Starting dashboard at http://localhost:{port}[/bold green]")
    uvicorn.run(app, host="0.0.0.0", port=port)
