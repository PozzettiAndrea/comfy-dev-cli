"""Generate HTML index from classified 3D nodes."""

import csv
import shutil
from collections import defaultdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from tqdm import tqdm

console = Console()


def find_latest_csv(data_dir, pattern):
    """Find the latest CSV file matching pattern."""
    files = list(data_dir.glob(pattern))
    if not files:
        return None
    return sorted(files)[-1]


def generate_index(input_file=None, skip_clone=False, skip_media=False):
    """Generate HTML index from classified nodes.

    Args:
        input_file: Override input CSV (default: latest ai_3d_nodes_*.csv)
        skip_clone: Skip repo cloning for node extraction (faster)
        skip_media: Skip media fetching (faster)
    """
    from config import get_3d_index_config
    from .utils.github import extract_github_info, fetch_readme
    from .utils.media import extract_media_from_readme, fetch_repo_media, clean_readme_for_search
    from .utils.node_parser import extract_repo_nodes
    from .utils.html_builder import generate_html, CATEGORIES

    config = get_3d_index_config()
    base_dir = Path(config["output"]["base_dir"])
    data_dir = base_dir / config["output"]["data_dir"]
    clone_dir = Path(config["cache"]["clone_dir"])

    # Find input file
    if input_file:
        input_csv = Path(input_file)
    else:
        input_csv = find_latest_csv(data_dir, "ai_3d_nodes_*.csv")
        if not input_csv:
            console.print("[red]No ai_3d_nodes_*.csv found[/red]")
            return

    console.print(f"Reading {input_csv}...")

    # Load nodes
    nodes_by_category = defaultdict(list)
    with open(input_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("category", "other-3d")
            if category not in CATEGORIES:
                category = "other-3d"
            nodes_by_category[category].append(row)

    total = sum(len(nodes) for nodes in nodes_by_category.values())
    console.print(f"Found {total} packages in {len(nodes_by_category)} categories")

    # Sort by stars
    for category in nodes_by_category:
        nodes_by_category[category].sort(
            key=lambda n: int(n["stars"]) if n["stars"].isdigit() else 0,
            reverse=True
        )

    all_nodes = []
    for cat_nodes in nodes_by_category.values():
        all_nodes.extend(cat_nodes)

    # Step 1: Clone repos and extract node definitions
    node_defs = {}
    if not skip_clone:
        console.print("\n[bold]Step 1:[/bold] Extracting node definitions (cloning repos)...")
        clone_dir.mkdir(parents=True, exist_ok=True)

        max_workers_clone = config["workers"]["clone"]

        def extract_wrapper(row):
            return extract_repo_nodes(row, str(clone_dir))

        with ThreadPoolExecutor(max_workers=max_workers_clone) as executor:
            futures = {executor.submit(extract_wrapper, row): row for row in all_nodes}

            with tqdm(total=len(all_nodes), desc="Cloning & parsing", unit="repo") as pbar:
                for future in as_completed(futures):
                    github_url, nodes = future.result()
                    node_defs[github_url] = nodes
                    pbar.set_postfix(nodes=sum(len(n) for n in node_defs.values()))
                    pbar.update(1)

        total_nodes = sum(len(n) for n in node_defs.values())
        console.print(f"Extracted {total_nodes} node definitions")

        # Cleanup
        shutil.rmtree(clone_dir, ignore_errors=True)
    else:
        console.print("\n[dim]Skipping node extraction (--skip-clone)[/dim]")

    # Step 2: Fetch media and updated dates
    media_by_url = {}
    if not skip_media:
        console.print("\n[bold]Step 2:[/bold] Fetching media and dates from GitHub repos...")

        from .utils.github import fetch_repo_updated_at

        def fetch_node_media(node):
            github_url = node["github_url"]
            owner, repo = extract_github_info(github_url)

            if not owner or not repo:
                return github_url, [], "", ""

            readme, branch = fetch_readme(owner, repo)
            readme_media = extract_media_from_readme(readme, owner, repo, branch)
            repo_media = fetch_repo_media(owner, repo, branch)
            updated_at = fetch_repo_updated_at(owner, repo)

            readme_set = set(readme_media)
            all_media = readme_media + [m for m in repo_media if m not in readme_set]

            readme_text = clean_readme_for_search(readme)

            return github_url, all_media[:12], updated_at, readme_text

        max_workers_media = config["workers"]["media"]

        with ThreadPoolExecutor(max_workers=max_workers_media) as executor:
            futures = {executor.submit(fetch_node_media, node): node["github_url"] for node in all_nodes}

            with tqdm(total=len(all_nodes), desc="Fetching media", unit="repo") as pbar:
                for future in as_completed(futures):
                    try:
                        github_url, media, updated_at, readme = future.result()
                        media_by_url[github_url] = (media, updated_at, readme)
                    except Exception:
                        github_url = futures[future]
                        media_by_url[github_url] = ([], "", "")
                    pbar.update(1)
    else:
        console.print("\n[dim]Skipping media fetching (--skip-media)[/dim]")

    # Build final structure (flat list)
    all_nodes_with_media = []
    for node in all_nodes:
        media, updated_at, readme = media_by_url.get(node["github_url"], ([], "", ""))
        all_nodes_with_media.append((node, media, updated_at, readme))

    # Generate HTML
    console.print("\n[bold]Step 3:[/bold] Generating HTML...")
    template_file = data_dir / "template.html"
    if not template_file.exists():
        console.print(f"[red]Template file not found: {template_file}[/red]")
        return

    html = generate_html(all_nodes_with_media, node_defs, template_file)

    output_file = base_dir / config["output"]["html_file"]
    output_file.write_text(html)
    console.print(f"[green]Generated {output_file}[/green]")

    console.print("\n[green bold]Done![/green bold]")
