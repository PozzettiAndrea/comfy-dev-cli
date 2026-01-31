"""Regex patterns for extracting links from READMEs and code."""

import re

# =============================================================================
# HuggingFace Patterns
# =============================================================================

# Direct HuggingFace URLs
HF_URL_PATTERNS = [
    # Full URLs: https://huggingface.co/org/model
    re.compile(r'https?://(?:www\.)?huggingface\.co/([^/\s]+/[^/\s]+)(?:/|$|\s|\)|\])', re.IGNORECASE),
    # Short URLs: https://hf.co/org/model
    re.compile(r'https?://hf\.co/([^/\s]+/[^/\s]+)(?:/|$|\s|\)|\])', re.IGNORECASE),
]

# from_pretrained patterns in code/README
HF_PRETRAINED_PATTERNS = [
    # "org/model" style references
    re.compile(r'from_pretrained\s*\(\s*["\']([^"\']+/[^"\']+)["\']', re.IGNORECASE),
    # Explicit HF references in markdown/text
    re.compile(r'huggingface\.co/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)', re.IGNORECASE),
    re.compile(r'hf\.co/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)', re.IGNORECASE),
]

# Model card badge patterns
HF_BADGE_PATTERNS = [
    re.compile(r'\[!\[.*?\]\(https://huggingface\.co/.*?badge.*?\)\]\((https://huggingface\.co/[^)]+)\)', re.IGNORECASE),
    re.compile(r'img\.shields\.io/badge/.*?huggingface', re.IGNORECASE),
]


# =============================================================================
# Paper/ArXiv Patterns
# =============================================================================

ARXIV_PATTERNS = [
    # Full arXiv URLs
    re.compile(r'https?://arxiv\.org/abs/(\d{4}\.\d{4,5})', re.IGNORECASE),
    re.compile(r'https?://arxiv\.org/pdf/(\d{4}\.\d{4,5})', re.IGNORECASE),
    # arXiv: prefix style
    re.compile(r'arXiv[:\s]+(\d{4}\.\d{4,5})', re.IGNORECASE),
    # Bare arXiv IDs with context
    re.compile(r'\[(\d{4}\.\d{4,5})\]', re.IGNORECASE),
]

PAPER_URL_PATTERNS = [
    # Papers with Code
    re.compile(r'https?://paperswithcode\.com/paper/([a-zA-Z0-9_-]+)', re.IGNORECASE),
    # OpenReview
    re.compile(r'https?://openreview\.net/(?:forum|pdf)\?id=([a-zA-Z0-9_-]+)', re.IGNORECASE),
    # Generic PDF links that look like papers
    re.compile(r'https?://[^\s]+/papers?/[^\s]+\.pdf', re.IGNORECASE),
    # Project page PDF links
    re.compile(r'https?://[^\s]+\.pdf', re.IGNORECASE),
]


# =============================================================================
# Project Website Patterns
# =============================================================================

# Project page patterns - look for links labeled as project/demo pages
PROJECT_PAGE_PATTERNS = [
    # Common project page labeling
    re.compile(r'\[(?:project\s*page|demo|website|homepage)\]\s*\((https?://[^\)]+)\)', re.IGNORECASE),
    # GitHub pages
    re.compile(r'https?://([a-zA-Z0-9_-]+)\.github\.io/([a-zA-Z0-9_-]+)', re.IGNORECASE),
    # io domains often used for projects
    re.compile(r'https?://([a-zA-Z0-9_-]+)\.(?:io|ai|app)/([a-zA-Z0-9_/-]*)', re.IGNORECASE),
]

# URLs to exclude as project websites (documentation, badges, etc.)
EXCLUDE_WEBSITE_PATTERNS = [
    re.compile(r'readthedocs\.', re.IGNORECASE),
    re.compile(r'docs\.[a-z]+\.', re.IGNORECASE),
    re.compile(r'shields\.io', re.IGNORECASE),
    re.compile(r'badge', re.IGNORECASE),
    re.compile(r'github\.com', re.IGNORECASE),
    re.compile(r'huggingface\.co', re.IGNORECASE),
    re.compile(r'arxiv\.org', re.IGNORECASE),
    re.compile(r'pypi\.org', re.IGNORECASE),
    re.compile(r'anaconda\.org', re.IGNORECASE),
]


# =============================================================================
# GitHub URL Parsing
# =============================================================================

GITHUB_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?',
    re.IGNORECASE
)

# owner/repo shorthand
GITHUB_SHORTHAND_PATTERN = re.compile(
    r'^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$'
)


def parse_github_url(url_or_shorthand):
    """Parse GitHub URL or owner/repo shorthand into (owner, repo) tuple."""
    # Try full URL first
    match = GITHUB_URL_PATTERN.search(url_or_shorthand)
    if match:
        repo = match.group(2)
        if repo.endswith('.git'):
            repo = repo[:-4]
        return match.group(1), repo

    # Try shorthand
    match = GITHUB_SHORTHAND_PATTERN.match(url_or_shorthand.strip())
    if match:
        return match.group(1), match.group(2)

    return None, None
