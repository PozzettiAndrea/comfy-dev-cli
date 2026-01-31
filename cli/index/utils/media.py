"""Media detection and fetching utilities for 3D index generation."""

import re
import json
from urllib.request import urlopen, Request

# Media file extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi'}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS


def normalize_url(url, owner, repo, branch):
    """Convert relative URLs and GitHub blob URLs to raw URLs."""
    if not url:
        return ""

    # Convert GitHub blob URLs to raw URLs
    blob_match = re.match(r'https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)', url)
    if blob_match:
        return f"https://raw.githubusercontent.com/{blob_match.group(1)}/{blob_match.group(2)}/{blob_match.group(3)}/{blob_match.group(4)}"

    if url.startswith(('http://', 'https://')):
        return url
    url = url.lstrip('./')
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{url}"


def is_media_url(url):
    """Check if URL points to a media file."""
    url_lower = url.lower().split('?')[0]
    # Check file extensions
    if any(url_lower.endswith(ext) for ext in MEDIA_EXTS):
        return True
    # GitHub user-attachments (no extension, but can be images or videos)
    if 'github.com/user-attachments/assets/' in url_lower:
        return True
    # GitHub repo assets (format: github.com/{owner}/{repo}/assets/{user_id}/{uuid})
    if re.search(r'github\.com/[^/]+/[^/]+/assets/\d+/', url_lower):
        return True
    return False


def detect_media_type(url):
    """Detect if URL is video or image via HEAD request.

    Returns 'video', 'image', or None.
    """
    url_lower = url.lower().split('?')[0]
    if any(url_lower.endswith(ext) for ext in VIDEO_EXTS):
        return 'video'
    if any(url_lower.endswith(ext) for ext in IMAGE_EXTS):
        return 'image'

    # For extensionless URLs (like GitHub user-attachments), check Content-Type
    if 'user-attachments/assets/' in url or re.search(r'/assets/\d+/', url):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urlopen(req, timeout=10) as resp:
                content_type = resp.headers.get('Content-Type', '').lower()
                if 'video' in content_type:
                    return 'video'
                if 'image' in content_type:
                    return 'image'
        except Exception:
            pass
    return 'image'  # Default to image


def extract_media_from_readme(readme_content, owner, repo, branch):
    """Extract media URLs from README content."""
    media = []

    # Markdown images
    img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
    for match in re.finditer(img_pattern, readme_content):
        url = match.group(1).strip()
        media.append(normalize_url(url, owner, repo, branch))

    # HTML images
    html_img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    for match in re.finditer(html_img_pattern, readme_content, re.IGNORECASE):
        url = match.group(1).strip()
        media.append(normalize_url(url, owner, repo, branch))

    # Videos
    video_pattern = r'<video[^>]+src=["\']([^"\']+)["\']|<source[^>]+src=["\']([^"\']+)["\']'
    for match in re.finditer(video_pattern, readme_content, re.IGNORECASE):
        url = (match.group(1) or match.group(2)).strip()
        media.append(normalize_url(url, owner, repo, branch))

    # Standalone GitHub asset URLs
    asset_pattern = r'https://github\.com/(?:user-attachments/assets/[a-f0-9-]+|[^/]+/[^/]+/assets/\d+/[a-f0-9-]+)'
    for match in re.finditer(asset_pattern, readme_content):
        url = match.group(0).strip()
        if url not in media:
            media.append(url)

    return [url for url in media if url and is_media_url(url)]


def fetch_repo_media(owner, repo, branch, timeout=15):
    """Fetch list of media files from repo via GitHub API."""
    media = []
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        req = Request(url, headers={"User-Agent": "ComfyUI-3D-Index"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        for item in data.get("tree", []):
            if item["type"] == "blob":
                path = item["path"].lower()
                if any(path.endswith(ext) for ext in MEDIA_EXTS):
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item['path']}"
                    media.append(raw_url)
    except Exception:
        pass

    return media


def clean_readme_for_search(readme):
    """Clean README content for search indexing."""
    if not readme:
        return ""
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', readme)
    # Remove images
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Limit size
    return text[:5000]
