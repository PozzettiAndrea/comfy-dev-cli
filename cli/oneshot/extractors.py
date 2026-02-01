"""Extraction functions for HuggingFace, papers, and project websites."""

import json
import os
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

from .patterns import (
    HF_URL_PATTERNS,
    HF_PRETRAINED_PATTERNS,
    HF_BADGE_PATTERNS,
    ARXIV_PATTERNS,
    PAPER_URL_PATTERNS,
    PROJECT_PAGE_PATTERNS,
    EXCLUDE_WEBSITE_PATTERNS,
)


def _clean_hf_url(url):
    """Clean up a HuggingFace URL, removing trailing junk."""
    # Remove trailing markdown/parentheses junk
    url = url.rstrip('.,;:)]\'"')
    # Handle double parens
    while url.endswith(')'):
        url = url[:-1]
    # Remove query params if they look like search artifacts
    if '?' in url and 'search=' in url:
        url = url.split('?')[0]
    return url


def extract_huggingface_links(text, repo_name=None, org=None):
    """
    Extract HuggingFace model links from text (README, description, etc.).

    Returns list of HF URLs found.
    """
    if not text:
        return []

    found = set()

    # Direct URL patterns
    for pattern in HF_URL_PATTERNS:
        for match in pattern.finditer(text):
            model_path = match.group(1)
            # Clean up trailing punctuation
            model_path = model_path.rstrip('.,;:)]\'"')
            url = f"https://huggingface.co/{model_path}"
            url = _clean_hf_url(url)
            found.add(url)

    # from_pretrained patterns
    for pattern in HF_PRETRAINED_PATTERNS:
        for match in pattern.finditer(text):
            model_path = match.group(1)
            # Skip common non-HF patterns
            if '/' in model_path and not model_path.startswith(('.', '~', '/')):
                url = f"https://huggingface.co/{model_path}"
                url = _clean_hf_url(url)
                found.add(url)

    # Badge patterns
    for pattern in HF_BADGE_PATTERNS:
        for match in pattern.finditer(text):
            if match.lastindex and match.lastindex >= 1:
                url = _clean_hf_url(match.group(1))
                found.add(url)

    return sorted(found)


def search_huggingface_api(repo_name, org=None):
    """
    Search HuggingFace Hub API for models matching repo name or org.

    Returns list of model info dicts.
    """
    results = []

    # Search strategies
    search_terms = [repo_name]
    if org:
        search_terms.append(org)

    for term in search_terms:
        try:
            # Search by model name
            url = f"https://huggingface.co/api/models?search={term}&limit=10"
            req = Request(url, headers={"User-Agent": "repo-validator/1.0"})
            with urlopen(req, timeout=10) as resp:
                models = json.loads(resp.read())
                for model in models:
                    model_id = model.get("modelId", "")
                    # Filter for relevant matches
                    if term.lower() in model_id.lower():
                        results.append({
                            "id": model_id,
                            "url": f"https://huggingface.co/{model_id}",
                            "downloads": model.get("downloads", 0),
                            "likes": model.get("likes", 0),
                        })
        except (HTTPError, URLError, json.JSONDecodeError):
            pass

    # Also try direct author search if org provided
    if org:
        try:
            url = f"https://huggingface.co/api/models?author={org}&limit=20"
            req = Request(url, headers={"User-Agent": "repo-validator/1.0"})
            with urlopen(req, timeout=10) as resp:
                models = json.loads(resp.read())
                for model in models:
                    model_id = model.get("modelId", "")
                    # Check if model name matches repo name
                    if repo_name.lower() in model_id.lower():
                        results.append({
                            "id": model_id,
                            "url": f"https://huggingface.co/{model_id}",
                            "downloads": model.get("downloads", 0),
                            "likes": model.get("likes", 0),
                        })
        except (HTTPError, URLError, json.JSONDecodeError):
            pass

    # Deduplicate by model ID
    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)

    return unique


def extract_paper_links(text):
    """
    Extract paper links (arXiv, OpenReview, etc.) from text.

    Returns list of paper URLs/IDs found.
    """
    if not text:
        return []

    found = []

    # ArXiv patterns
    for pattern in ARXIV_PATTERNS:
        for match in pattern.finditer(text):
            arxiv_id = match.group(1)
            url = f"https://arxiv.org/abs/{arxiv_id}"
            if url not in found:
                found.append(url)

    # Other paper URL patterns
    for pattern in PAPER_URL_PATTERNS:
        for match in pattern.finditer(text):
            url = match.group(0)
            # Skip if too generic (just a PDF link with no context)
            if 'arxiv' in url.lower() or 'paper' in url.lower() or 'openreview' in url.lower():
                if url not in found:
                    found.append(url)

    return found


def extract_website_links(text, repo_name=None):
    """
    Extract project website links from text.

    Returns first valid project website found, or None.
    """
    if not text:
        return None

    candidates = []

    # Look for explicit project page labels first
    for pattern in PROJECT_PAGE_PATTERNS:
        for match in pattern.finditer(text):
            url = match.group(0)
            # Extract actual URL from markdown link if present
            if '](' in url:
                url = url.split('](')[-1].rstrip(')')
            candidates.append(url)

    # Filter out excluded domains
    for url in candidates:
        excluded = False
        for exclude_pattern in EXCLUDE_WEBSITE_PATTERNS:
            if exclude_pattern.search(url):
                excluded = True
                break
        if not excluded:
            return url

    return None


def fetch_github_metadata(owner, repo, token=None):
    """
    Fetch GitHub repo metadata via API.

    Returns dict with stars, language, license, etc.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {
        "User-Agent": "repo-validator/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                "full_name": data.get("full_name"),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "language": data.get("language"),
                "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
                "topics": data.get("topics", []),
                "updated_at": data.get("updated_at"),
                "default_branch": data.get("default_branch", "main"),
            }
    except HTTPError as e:
        if e.code == 404:
            return {"error": "Repository not found"}
        elif e.code == 403:
            return {"error": "Rate limited or requires authentication"}
        else:
            return {"error": f"HTTP {e.code}"}
    except (URLError, json.JSONDecodeError) as e:
        return {"error": str(e)}


def fetch_readme(owner, repo, token=None, default_branch="main"):
    """
    Fetch README content from GitHub repo.

    Tries multiple common README filenames and branches.
    """
    headers = {
        "User-Agent": "repo-validator/1.0",
        "Accept": "application/vnd.github.v3.raw",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Common README filenames
    readme_names = ["README.md", "readme.md", "README.rst", "README.txt", "README"]
    branches = [default_branch, "main", "master"]

    for branch in branches:
        for readme in readme_names:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{readme}"
            try:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=10) as resp:
                    return resp.read().decode('utf-8', errors='ignore')
            except (HTTPError, URLError):
                continue

    return None


def _format_size(size_bytes):
    """Format bytes into human-readable size."""
    if size_bytes is None:
        return "unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def download_paper_pdf(paper_url, dest_path):
    """
    Download PDF from any URL (arXiv or direct PDF link).

    Args:
        paper_url: arXiv URL or direct PDF URL
        dest_path: Path to save the PDF

    Returns:
        True on success, False on failure
    """
    # Check if it's an arXiv URL and convert to PDF format
    arxiv_id_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', paper_url, re.IGNORECASE)
    if arxiv_id_match:
        arxiv_id = arxiv_id_match.group(1)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    else:
        # Assume it's a direct PDF URL
        pdf_url = paper_url

    try:
        req = Request(pdf_url, headers={"User-Agent": "oneshot-wrapper/1.0"})
        with urlopen(req, timeout=60) as resp:
            dest_path = Path(dest_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                f.write(resp.read())
        return True
    except (HTTPError, URLError):
        return False


def fetch_hf_model_files(model_id):
    """
    Fetch file listing with sizes from HuggingFace API.

    Args:
        model_id: HuggingFace model ID (e.g., "VAST-AI/UniRig")

    Returns:
        Dict with model info and file listing, or None on failure
    """
    # Clean up model_id - extract from URL if needed
    if 'huggingface.co/' in model_id:
        match = re.search(r'huggingface\.co/([^/]+/[^/\s]+)', model_id)
        if match:
            model_id = match.group(1)

    # Remove trailing slashes/junk
    model_id = model_id.rstrip('/').split('?')[0]

    try:
        # Get file tree from HF API (recursive to get all files in folders)
        tree_url = f"https://huggingface.co/api/models/{model_id}/tree/main?recursive=true"
        req = Request(tree_url, headers={"User-Agent": "oneshot-wrapper/1.0"})

        with urlopen(req, timeout=60) as resp:
            files_data = json.loads(resp.read())

        files = []
        total_size = 0

        for item in files_data:
            if item.get("type") == "file":
                size = item.get("size", 0) or 0
                files.append({
                    "path": item.get("path", ""),
                    "size_bytes": size,
                    "size_human": _format_size(size),
                })
                total_size += size

        return {
            "model_id": model_id,
            "url": f"https://huggingface.co/{model_id}",
            "files": files,
            "total_size_bytes": total_size,
            "total_size_human": _format_size(total_size),
        }

    except (HTTPError, URLError, json.JSONDecodeError):
        return None


def convert_pdf_to_markdown(pdf_path, md_path, strip_references=True):
    """
    Convert PDF to markdown using marker-pdf.

    Args:
        pdf_path: Path to input PDF
        md_path: Path for output markdown
        strip_references: If True, remove References section

    Returns:
        True on success, False on failure
    """
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
    except ImportError:
        return None  # marker-pdf not installed

    try:
        models = create_model_dict()
        converter = PdfConverter(artifact_dict=models)
        rendered = converter(str(pdf_path))

        md_content = rendered.markdown

        # Strip references section if requested
        if strip_references:
            for ref_header in ["# References", "## References", "# REFERENCES", "## REFERENCES"]:
                if ref_header in md_content:
                    md_content = md_content.split(ref_header)[0].strip()
                    break

        md_path = Path(md_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(md_path, 'w') as f:
            f.write(md_content)

        return True

    except Exception:
        return False


# Paper markdown caching
PAPER_CACHE_DIR = Path(__file__).parent.parent / "paper-mds"


def _sanitize_cache_key(text):
    """Sanitize text for use as a cache filename."""
    # Lowercase, replace spaces and special chars
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = text.strip('-')
    return text[:100]  # Limit length


def get_paper_cache_key(paper_url):
    """
    Generate cache key from paper URL.

    Uses arXiv ID if available, otherwise uses URL hash.
    """
    # Try to extract arXiv ID
    arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', paper_url, re.IGNORECASE)
    if arxiv_match:
        return f"arxiv-{arxiv_match.group(1)}"

    # Fallback: use sanitized URL
    return _sanitize_cache_key(paper_url.split('/')[-1].replace('.pdf', ''))


def get_cached_paper_md(cache_key):
    """
    Check if a paper markdown exists in cache.

    Returns path if exists, None otherwise.
    """
    PAPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = PAPER_CACHE_DIR / f"{cache_key}.md"
    if cache_path.exists():
        return cache_path
    return None


def save_paper_to_cache(cache_key, md_content):
    """Save paper markdown to cache."""
    PAPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = PAPER_CACHE_DIR / f"{cache_key}.md"
    cache_path.write_text(md_content)
    return cache_path
