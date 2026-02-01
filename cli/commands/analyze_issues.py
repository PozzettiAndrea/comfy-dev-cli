"""Analyze GitHub issues using Claude Code to find probable causes."""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

console = Console()

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent
COMMAND_CENTER_DIR = ROOT_DIR / "command-center"
ANALYSIS_DIR = COMMAND_CENTER_DIR / "issue_analysis"
ANALYSIS_META_FILE = ANALYSIS_DIR / "_meta.json"
ALL_REPOS_DIR = ROOT_DIR.parent / "all_repos"


def issue_hash(issue) -> str:
    """Generate hash for issue to detect changes."""
    # Include number, title, body, and comment count
    body = issue.body or ""
    content = f"{issue.number}|{issue.title}|{body}|{issue.comments}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_analysis_cache() -> dict:
    """Load existing analysis results from folder structure."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Load metadata
    meta = {"last_run": None}
    if ANALYSIS_META_FILE.exists():
        with open(ANALYSIS_META_FILE) as f:
            meta = json.load(f)

    # Load per-repo analysis files
    analyses = {}
    for repo_file in ANALYSIS_DIR.glob("*.json"):
        if repo_file.name.startswith("_"):
            continue
        repo_name = repo_file.stem
        with open(repo_file) as f:
            analyses[repo_name] = json.load(f)

    return {"last_run": meta.get("last_run"), "analyses": analyses}


def save_repo_analysis(repo_name: str, data: dict):
    """Save analysis for a single repo."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    repo_file = ANALYSIS_DIR / f"{repo_name}.json"
    with open(repo_file, "w") as f:
        json.dump(data, f, indent=2)


def save_analysis_meta(last_run: str):
    """Save metadata (last run timestamp)."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ANALYSIS_META_FILE, "w") as f:
        json.dump({"last_run": last_run}, f, indent=2)


def get_file_tree(repo_path: Path, max_depth: int = 3) -> str:
    """Get a simple file tree of the repo."""
    lines = []

    def walk(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return

        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        # Filter out common non-essential directories
        skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "eggs", ".eggs"}
        items = [i for i in items if i.name not in skip_dirs]

        for i, item in enumerate(items[:20]):  # Limit items per directory
            is_last = i == len(items[:20]) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item.name}")

            if item.is_dir():
                extension = "    " if is_last else "│   "
                walk(item, prefix + extension, depth + 1)

    walk(repo_path)
    return "\n".join(lines[:100])  # Limit total lines


def format_issues_for_prompt(issues: list) -> str:
    """Format issues for the Claude prompt."""
    formatted = []
    for issue in issues:
        body = issue.body or "(No description)"
        # Truncate very long bodies
        if len(body) > 2000:
            body = body[:2000] + "\n... (truncated)"

        labels = ", ".join([l.name for l in issue.labels]) or "None"

        formatted.append(f"""### Issue #{issue.number}: {issue.title}
- URL: {issue.html_url}
- Author: {issue.user.login}
- Labels: {labels}
- Created: {issue.created_at.strftime("%Y-%m-%d")}
- Comments: {issue.comments}

{body}
""")
    return "\n---\n".join(formatted)


def analyze_repo_issues(repo_name: str, repo_path: Path, issues: list) -> list:
    """Spawn Claude Code to analyze issues for a repo."""

    file_tree = get_file_tree(repo_path)
    issues_text = format_issues_for_prompt(issues)
    issue_numbers = [i.number for i in issues]

    prompt = f'''You are analyzing GitHub issues for the {repo_name} repository to identify probable causes and fixes.

## Repository Structure
```
{file_tree}
```

## Open Issues to Analyze
{issues_text}

---

For EACH issue above, analyze the code and provide your assessment with epistemic humility - express uncertainty where appropriate.

Output a JSON array with one object per issue:

```json
[
  {{
    "number": <issue_number>,
    "summary": "50-word max summary for quick scanning",
    "probable_cause": "What's likely causing this (be specific but acknowledge uncertainty)",
    "confidence": "low|medium|high",
    "effort": "quick-fix|moderate|major-refactor",
    "risk_of_regression": "low|medium|high",
    "uncertainty_notes": "What else could cause this? What would need verification?",
    "related_issues": [],
    "suggested_fix": "Specific fix suggestion with file paths if applicable",
    "related_files": ["list", "of", "relevant", "files"],
    "category": "bug|configuration|dependency|documentation|feature-request|user-error"
  }}
]
```

Important:
- Be honest about uncertainty - say "I'm not sure" rather than guess confidently
- For low confidence, explain what information would help
- Consider whether a quick fix could make things worse (risk_of_regression)
- For user-error issues, explain what the user should do differently
- For feature requests, acknowledge them as such and set effort appropriately
- Output ONLY the JSON array, no other text
'''

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            timeout=300,  # 5 min timeout
        )

        output = result.stdout.strip()

        # Try to extract JSON from the output
        # Claude might wrap it in markdown code blocks
        if "```json" in output:
            start = output.find("```json") + 7
            end = output.find("```", start)
            output = output[start:end].strip()
        elif "```" in output:
            start = output.find("```") + 3
            end = output.find("```", start)
            output = output[start:end].strip()

        analyses = json.loads(output)
        return analyses

    except subprocess.TimeoutExpired:
        console.print(f"[yellow]Timeout analyzing {repo_name}[/yellow]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Failed to parse Claude response for {repo_name}: {e}[/yellow]")
        console.print(f"[dim]Response was: {result.stdout[:500]}...[/dim]")
        return []
    except Exception as e:
        console.print(f"[red]Error analyzing {repo_name}: {e}[/red]")
        return []


def analyze_issues(repo_name: str | None = None, force: bool = False, workers: int = 1):
    """Analyze issues across repos using Claude Code."""
    from github import Github
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from config import get_all_repos, get_github_token, GITHUB_OWNER

    token = get_github_token()
    if not token:
        console.print("[red]GITHUB_TOKEN not set.[/red]")
        return

    g = Github(token)
    repos = get_all_repos()

    if repo_name:
        repos = [r for r in repos if r.name == repo_name]
        if not repos:
            console.print(f"[red]Repo '{repo_name}' not found.[/red]")
            return

    # Load existing cache
    cache = load_analysis_cache()

    # Track stats
    total_analyzed = 0
    repos_processed = 0
    repos_skipped = 0

    # Filter to repos with issues first (parallel scanning)
    repos_with_issues = []
    console.print(f"[dim]Scanning {len(repos)} repos for open issues (8 threads)...[/dim]")

    def fetch_issues(repo):
        try:
            gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo.name}")
            issues = [i for i in gh_repo.get_issues(state="open") if not i.pull_request]
            return (repo, issues) if issues else None
        except Exception as e:
            tqdm.write(f"[red]Error checking {repo.name}: {e}[/red]")
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_issues, repo): repo for repo in repos}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Scanning repos", unit="repo"):
            result = future.result()
            if result:
                repos_with_issues.append(result)

    if not repos_with_issues:
        console.print("[yellow]No repos with open issues found.[/yellow]")
        return

    console.print(f"\n[cyan]Found {len(repos_with_issues)} repos with open issues[/cyan]")
    console.print(f"[cyan]Using {workers} parallel worker(s)[/cyan]\n")

    def process_repo(repo_issues_tuple):
        """Process a single repo - used by thread pool."""
        repo, issues = repo_issues_tuple
        result = {"repo": repo.name, "analyzed": 0, "skipped": False, "error": None}

        try:
            # Get repo path (from clone-all or clone fresh)
            repo_path = ALL_REPOS_DIR / repo.name

            if not repo_path.exists():
                tqdm.write(f"  Cloning {repo.name}...")
                subprocess.run(
                    ["git", "clone", "--depth", "1",
                     f"https://github.com/{GITHUB_OWNER}/{repo.name}.git",
                     str(repo_path)],
                    capture_output=True,
                    check=True,
                )

            # Check which issues need analysis
            cached_repo = cache["analyses"].get(repo.name, {"issues": []})
            cached_hashes = {i["hash"] for i in cached_repo.get("issues", [])}

            issues_to_analyze = []
            for issue in issues:
                h = issue_hash(issue)
                if force or h not in cached_hashes:
                    issues_to_analyze.append(issue)

            if not issues_to_analyze:
                result["skipped"] = True
                return result

            # Analyze with Claude
            tqdm.write(f"  Analyzing {len(issues_to_analyze)} issues in {repo.name}...")
            analyses = analyze_repo_issues(repo.name, repo_path, issues_to_analyze)

            if analyses:
                # Merge with existing cache
                existing_issues = {i["number"]: i for i in cached_repo.get("issues", [])}

                for analysis in analyses:
                    issue_num = analysis["number"]
                    # Find matching issue for metadata
                    matching = next((i for i in issues_to_analyze if i.number == issue_num), None)
                    if matching:
                        # Preserve status if issue was already analyzed
                        old_status = existing_issues.get(issue_num, {}).get("status", "new")

                        existing_issues[issue_num] = {
                            "number": issue_num,
                            "hash": issue_hash(matching),
                            "title": matching.title,
                            "url": matching.html_url,
                            "author": matching.user.login,
                            "status": old_status,  # new | waiting-for-confirmation | closed
                            "comments_at_analysis": matching.comments,
                            "analysis": {
                                "summary": analysis.get("summary", ""),
                                "probable_cause": analysis.get("probable_cause", "Unknown"),
                                "confidence": analysis.get("confidence", "medium"),
                                "effort": analysis.get("effort", "moderate"),
                                "risk_of_regression": analysis.get("risk_of_regression", "medium"),
                                "uncertainty_notes": analysis.get("uncertainty_notes", ""),
                                "related_issues": analysis.get("related_issues", []),
                                "suggested_fix": analysis.get("suggested_fix", "Unknown"),
                                "related_files": analysis.get("related_files", []),
                                "category": analysis.get("category", "bug"),
                            },
                            "analyzed_at": datetime.now().isoformat(),
                        }
                        result["analyzed"] += 1

                # Save this repo immediately (per-repo files)
                save_repo_analysis(repo.name, {"issues": list(existing_issues.values())})

        except Exception as e:
            result["error"] = str(e)

        return result

    # Process repos in parallel
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_repo, item): item[0].name for item in repos_with_issues}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Analyzing repos", unit="repo"):
            repo_name = futures[future]
            try:
                result = future.result()
                if result["error"]:
                    console.print(f"[red]Error processing {repo_name}: {result['error']}[/red]")
                elif result["skipped"]:
                    repos_skipped += 1
                else:
                    total_analyzed += result["analyzed"]
                    repos_processed += 1
            except Exception as e:
                console.print(f"[red]Error processing {repo_name}: {e}[/red]")

    # Save metadata
    save_analysis_meta(datetime.now().isoformat())

    # Summary
    console.print()
    console.print(Panel(
        f"[green]Analyzed {total_analyzed} issues across {repos_processed} repos[/green]\n"
        f"[dim]Skipped {repos_skipped} repos (no changes)[/dim]\n"
        f"[dim]Results saved to: {ANALYSIS_DIR}/[/dim]",
        title="Analysis Complete",
    ))
