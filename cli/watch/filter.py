"""Pre-filtering logic for 3D AI Watcher."""

import re


def matches_keywords(text: str, include_keywords: list, exclude_keywords: list) -> bool:
    """Check if text matches include keywords and doesn't match exclude keywords.

    Args:
        text: Text to check (title, description, README, etc.)
        include_keywords: List of keywords - any match = include
        exclude_keywords: List of keywords - any match = exclude

    Returns:
        True if text should be included, False otherwise.
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check excludes first
    for keyword in exclude_keywords:
        if keyword.lower() in text_lower:
            return False

    # Check includes
    for keyword in include_keywords:
        if keyword.lower() in text_lower:
            return True

    return False


def is_3d_relevant(title: str, description: str, readme: str = "",
                   include_keywords: list = None, exclude_keywords: list = None) -> tuple:
    """Check if a project is 3D-relevant based on title, description, and README.

    Returns:
        (is_relevant: bool, matched_keyword: str or None)
    """
    if include_keywords is None:
        include_keywords = [
            "3D", "3d", "mesh", "gaussian", "splat", "nerf",
            "reconstruction", "avatar", "rigging", "skeleton",
            "skinning", "depth", "point cloud", "pointcloud",
            "CAD", "SLAM", "photogrammetry", "volumetric", "voxel",
            "radiance field", "neural rendering", "scene reconstruction",
            "motion capture", "mocap", "body tracking", "pose estimation"
        ]

    if exclude_keywords is None:
        exclude_keywords = ["3D printing", "3D printer", "printer filament"]

    # Combine all text
    all_text = f"{title} {description} {readme}"
    all_text_lower = all_text.lower()

    # Check excludes first
    for keyword in exclude_keywords:
        if keyword.lower() in all_text_lower:
            return False, None

    # Check includes
    for keyword in include_keywords:
        if keyword.lower() in all_text_lower:
            return True, keyword

    return False, None


def extract_relevance_score(title: str, description: str, readme: str = "",
                            include_keywords: list = None) -> int:
    """Calculate a relevance score based on keyword matches.

    Higher score = more relevant to 3D AI.
    """
    if include_keywords is None:
        include_keywords = [
            "3D", "mesh", "gaussian", "splat", "nerf",
            "reconstruction", "avatar", "rigging", "skeleton",
            "depth", "point cloud", "CAD", "SLAM"
        ]

    all_text = f"{title} {description} {readme}".lower()
    score = 0

    for keyword in include_keywords:
        count = len(re.findall(re.escape(keyword.lower()), all_text))
        score += count

    return score
