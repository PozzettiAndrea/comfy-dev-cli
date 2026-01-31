"""Fetch all ComfyUI nodes from Manager and Registry."""

import csv
import json
import glob
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

from rich.console import Console
from tqdm import tqdm

console = Console()


def fetch_manager_nodes(config):
    """Fetch nodes from ComfyUI-Manager custom-node-list.json."""
    console.print("Fetching from ComfyUI-Manager...")
    manager_url = config["api"]["manager_url"]
    req = Request(manager_url)
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    nodes = data.get("custom_nodes", [])
    console.print(f"  Found {len(nodes)} nodes")
    return nodes


def fetch_registry_nodes(config):
    """Fetch all nodes from Comfy Registry API."""
    console.print("Fetching from Comfy Registry...")
    registry_url = config["api"]["registry_url"]
    nodes = []
    page = 1
    while True:
        url = f"{registry_url}?limit=100&page={page}"
        req = Request(url, headers={"User-Agent": "ComfyUI-3D-Index"})
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            nodes.extend(data.get("nodes", []))
            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1
            if page % 10 == 0:
                console.print(f"  Page {page}/{total_pages}...")
        except Exception as e:
            console.print(f"  [red]Error on page {page}: {e}[/red]")
            break
    console.print(f"  Found {len(nodes)} nodes")
    return nodes


def fetch_github_stats(config):
    """Fetch star counts from github-stats.json."""
    console.print("Fetching GitHub stats...")
    stats_url = config["api"]["stats_url"]
    req = Request(stats_url)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def find_latest_csv(data_dir, pattern):
    """Find the latest CSV file matching pattern."""
    files = list(data_dir.glob(pattern))
    if not files:
        return None
    return sorted(files)[-1]


def fetch_all(skip_readmes=False, workers=None):
    """Fetch all ComfyUI nodes from Manager and Registry.

    Args:
        skip_readmes: If True, don't fetch READMEs (faster, for testing)
        workers: Override worker count from config
    """
    from config import get_3d_index_config
    from .utils.github import extract_github_info, fetch_readme
    from .utils.readme_cache import ReadmeCache

    config = get_3d_index_config()
    base_dir = Path(config["output"]["base_dir"])
    data_dir = base_dir / config["output"]["data_dir"]
    readmes_dir = base_dir / config["output"]["readmes_dir"]

    data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize README cache
    readme_cache = ReadmeCache(readmes_dir, config["cache"]["readme_max_age_days"])

    # Fetch from both sources
    manager_nodes = fetch_manager_nodes(config)
    registry_nodes = fetch_registry_nodes(config)
    stats = fetch_github_stats(config)

    # Merge and deduplicate by GitHub repo URL
    import re
    seen_repos = {}

    def extract_info(node):
        repo_url = node.get("reference", "") or node.get("repository", "") or ""
        match = re.search(r"github\.com/([^/]+)/([^/\s]+)", repo_url)
        if match:
            return match.group(1), match.group(2).replace(".git", "").rstrip("/")
        return None, None

    # Process ComfyUI-Manager nodes first (priority source)
    for node in manager_nodes:
        owner, repo = extract_info(node)
        if owner and repo:
            key = f"{owner}/{repo}".lower()
            github_url = f"https://github.com/{owner}/{repo}"
            star_count = stats.get(github_url, {}).get("stars", 0)
            if key not in seen_repos:
                seen_repos[key] = (node, owner, repo, star_count)

    manager_count = len(seen_repos)
    console.print(f"After ComfyUI-Manager: {manager_count} unique repos")

    # Add Registry nodes (fill in missing)
    registry_added = 0
    for node in registry_nodes:
        repo_url = node.get("repository", "")
        owner, repo = extract_info({"reference": repo_url})
        if owner and repo:
            key = f"{owner}/{repo}".lower()
            if key not in seen_repos:
                node_dict = {
                    "title": node.get("name", ""),
                    "description": node.get("description", ""),
                    "reference": repo_url
                }
                star_count = node.get("github_stars", 0)
                seen_repos[key] = (node_dict, owner, repo, star_count)
                registry_added += 1

    console.print(f"Added {registry_added} new repos from Registry")

    unique_nodes = list(seen_repos.values())
    total = len(unique_nodes)
    console.print(f"Total unique GitHub repos: {total}")

    # Prepare work items
    def process_node(args):
        idx, node, owner, repo, stars = args
        name = node.get("title") or node.get("name") or repo
        desc = node.get("description", "")[:500]
        github_url = f"https://github.com/{owner}/{repo}"

        # Use README cache
        if not skip_readmes:
            readme_cache.get(github_url)  # This caches the README

        return (idx, [name, github_url, stars, owner, desc])

    work_items = [(i, node, owner, repo, stars) for i, (node, owner, repo, stars) in enumerate(unique_nodes)]
    results = [None] * total

    max_workers = workers or config["workers"]["fetch_readme"]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_node, item): item[0] for item in work_items}

        with tqdm(total=total, desc="Processing nodes", unit="repo") as pbar:
            for future in as_completed(futures):
                idx, row = future.result()
                results[idx] = row
                pbar.update(1)

    # Write CSV (without README column - READMEs are cached separately)
    date_tag = datetime.now().strftime("%Y-%m-%d")
    output_file = data_dir / f"all_comfyui_nodes_{date_tag}.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "github_url", "stars", "author", "description"])
        for row in results:
            if row:
                writer.writerow(row)

    console.print(f"\n[green]Done! Saved {total} nodes to {output_file}[/green]")

    # Print cache stats
    cache_stats = readme_cache.get_stats()
    console.print(f"[dim]README cache: {cache_stats['total_cached']} files, {cache_stats['total_size_mb']} MB[/dim]")
