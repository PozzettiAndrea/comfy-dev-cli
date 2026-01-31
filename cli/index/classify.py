"""Classify nodes for 3D relevance using DeepSeek via OpenRouter."""

import csv
import json
import glob
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request

from rich.console import Console
from rich.prompt import Prompt
from tqdm import tqdm

console = Console()


def load_skip_set(data_dir):
    """Load repos to skip from skip_list.json."""
    skip_file = data_dir / "skip_list.json"
    if skip_file.exists():
        try:
            with open(skip_file) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_skip_set(skip_set, data_dir):
    """Save skip list as single consolidated file."""
    skip_file = data_dir / "skip_list.json"
    with open(skip_file, "w") as f:
        json.dump(sorted(skip_set), f, indent=2)


def find_latest_csv(data_dir, pattern):
    """Find the latest CSV file matching pattern."""
    files = list(data_dir.glob(pattern))
    if not files:
        return None
    return sorted(files)[-1]


def classify_node(api_key, system_prompt, row, readme, config):
    """Classify a single node using DeepSeek."""
    name, github_url, stars, author, desc = row

    # Truncate readme
    truncate_len = config["classification"]["readme_truncate_chars"]
    readme_short = readme[:truncate_len] if readme else ""

    user_msg = f"Package: {name}\nURL: {github_url}\nAuthor: {author}\nDescription: {desc}\n\nREADME:\n{readme_short}"

    payload = json.dumps({
        "model": config["api"]["openrouter_model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": config["classification"]["max_tokens"],
        "temperature": config["classification"]["temperature"]
    }).encode()

    req = Request(config["api"]["openrouter_url"], data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ComfyUI-3D_nodes_index",
        "X-Title": "ComfyUI 3D Node Filter"
    })

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            # Try to parse JSON, handle if model wraps in markdown
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        return {"relevant": False, "confidence": "low", "category": "", "model_author": "", "description": "", "nodes_list": "", "_debug": str(e)[:200]}


def classify_nodes(input_file=None, top_n=None, force=False, workers=None):
    """Classify nodes for 3D relevance.

    Args:
        input_file: Override input CSV (default: latest all_comfyui_nodes_*.csv)
        top_n: Only classify top N by stars
        force: Re-classify even if in skip list
        workers: Override worker count
    """
    from config import get_3d_index_config, get_openrouter_key
    from .utils.readme_cache import ReadmeCache

    config = get_3d_index_config()
    base_dir = Path(config["output"]["base_dir"])
    data_dir = base_dir / config["output"]["data_dir"]
    readmes_dir = base_dir / config["output"]["readmes_dir"]

    # Get API key
    api_key = get_openrouter_key()
    if not api_key:
        api_key = Prompt.ask("OpenRouter API key")
        if not api_key:
            console.print("[red]API key required[/red]")
            return

    # Load system prompt
    prompt_file = data_dir / config["classification"]["prompt_file"]
    if not prompt_file.exists():
        console.print(f"[red]Prompt file not found: {prompt_file}[/red]")
        return
    system_prompt = prompt_file.read_text()

    # Find input file
    if input_file:
        input_csv = Path(input_file)
    else:
        input_csv = find_latest_csv(data_dir, "all_comfyui_nodes_*.csv")
        if not input_csv:
            console.print("[red]No all_comfyui_nodes_*.csv found[/red]")
            return

    console.print(f"Reading {input_csv}...")

    # Load nodes
    all_rows = []
    with open(input_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            all_rows.append(row)

    console.print(f"Found {len(all_rows)} total nodes")

    # Load skip list
    skip_set = set() if force else load_skip_set(data_dir)

    # Filter out already-skipped repos
    rows = []
    for row in all_rows:
        github_url = row[1].lower()
        if github_url not in skip_set:
            rows.append(row)

    skipped = len(all_rows) - len(rows)
    if skipped:
        console.print(f"Skipping {skipped} repos already in skip list")

    # Apply top_n filter
    if top_n:
        rows.sort(key=lambda r: int(r[2]) if r[2].isdigit() else 0, reverse=True)
        rows = rows[:top_n]
        console.print(f"Selected top {top_n} nodes by stars")

    if not rows:
        console.print("[yellow]No nodes to classify[/yellow]")
        return

    # Initialize README cache
    readme_cache = ReadmeCache(readmes_dir, config["cache"]["readme_max_age_days"])

    max_workers = workers or config["workers"]["classify"]
    console.print(f"Classifying {len(rows)} nodes with {max_workers} workers...")

    results_3d = []
    results_non_3d = []
    errors = []

    def process_row(row):
        github_url = row[1]
        readme = readme_cache.get(github_url)
        result = classify_node(api_key, system_prompt, row, readme, config)
        return row, result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_row, row): row for row in rows}

        with tqdm(total=len(rows), desc="Classifying", unit="node") as pbar:
            for future in as_completed(futures):
                row, result = future.result()

                if "_debug" in result:
                    errors.append((row[0], result["_debug"]))
                elif result.get("relevant"):
                    results_3d.append((row, result))
                else:
                    results_non_3d.append((row, result))

                pbar.set_postfix(found=len(results_3d), errs=len(errors))
                pbar.update(1)

    if errors:
        console.print(f"\n[red]{len(errors)} errors occurred. First 3:[/red]")
        for name, err in errors[:3]:
            console.print(f"  - {name}: {err}")

    # Update skip list with new non-3D
    for row, result in results_non_3d:
        skip_set.add(row[1].lower())
    save_skip_set(skip_set, data_dir)

    # Write outputs
    date_tag = datetime.now().strftime("%Y-%m-%d")
    csv_header = ["name", "github_url", "stars", "node_author", "model_author", "description", "nodes_list", "category", "confidence"]

    def write_results(filename, results):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            for row, result in results:
                writer.writerow([
                    row[0],  # name
                    row[1],  # github_url
                    row[2],  # stars
                    row[3],  # node_author
                    result.get("model_author", ""),
                    result.get("description", ""),
                    result.get("nodes_list", ""),
                    result.get("category", ""),
                    result.get("confidence", "")
                ])

    # Write 3D nodes
    output_3d = data_dir / f"ai_3d_nodes_{date_tag}.csv"
    console.print(f"\nWriting {len(results_3d)} 3D nodes to {output_3d}...")
    write_results(output_3d, results_3d)

    # Write non-3D nodes
    output_non_3d = data_dir / f"ai_non_3d_nodes_{date_tag}.csv"
    console.print(f"Writing {len(results_non_3d)} non-3D nodes to {output_non_3d}...")
    write_results(output_non_3d, results_non_3d)

    console.print(f"\n[green]Done! Found {len(results_3d)} 3D-relevant nodes.[/green]")
    console.print(f"[dim]Skip list now has {len(skip_set)} repos[/dim]")
