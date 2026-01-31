"""HTML generation utilities for 3D index."""

import json
from pathlib import Path

from .github import extract_github_info
from .media import detect_media_type

# Category display names and order
CATEGORIES = {
    "image-to-3d": "Image-to-3D",
    "text-to-3d": "Text-to-3D",
    "multi-view": "Multi-View Generation",
    "mesh-processing": "Mesh Processing",
    "texturing": "Texturing",
    "gaussian-splatting": "Gaussian Splatting",
    "rigging-animation": "Rigging & Animation",
    "depth-normal": "Depth & Normal",
    "visualization": "Visualization",
    "cad": "CAD",
    "human-body": "Human Body",
    "other-3d": "Other 3D"
}


def format_stars(stars):
    """Format star count (e.g., 3500 -> 3.5k)"""
    try:
        n = int(stars)
        if n >= 1000:
            return f"{n/1000:.1f}k".replace(".0k", "k")
        return str(n)
    except:
        return stars


def get_data_tag(model_author):
    """Get filter tag from model author."""
    author_lower = model_author.lower() if model_author else ""
    if "tencent" in author_lower:
        return "tencent"
    if "microsoft" in author_lower:
        return "microsoft"
    if "meta" in author_lower:
        return "meta"
    if "vast" in author_lower:
        return "vast-ai"
    if "stability" in author_lower:
        return "stability"
    return "community"


def generate_media_gallery(media_urls, media_types=None):
    """Generate HTML for media gallery."""
    if not media_urls:
        return ""

    media_types = media_types or {}
    items = []
    for url in media_urls[:6]:
        media_type = media_types.get(url, detect_media_type(url))
        if media_type == 'video':
            items.append(f'<video src="{url}" muted loop playsinline class="gallery-item" onclick="this.paused ? this.play() : this.pause()"></video>')
        else:
            items.append(f'<img src="{url}" alt="Preview" class="gallery-item" loading="lazy" onerror="this.style.display=\'none\'">')

    if not items:
        return ""

    return f'''<div class="media-gallery">{"".join(items)}</div>'''


def generate_card(node, media_urls, node_defs, updated_at, readme=""):
    """Generate HTML for a single card."""
    github_url = node["github_url"]
    _, repo_name = extract_github_info(github_url)
    name = repo_name or node["name"]
    stars_raw = node["stars"]
    stars = format_stars(stars_raw)
    node_author = node["node_author"]
    model_author = node["model_author"] or "Community"
    description = node["description"]
    category = node["category"]
    data_tag = get_data_tag(model_author)
    readme_escaped = readme.replace('"', '&quot;').replace("'", '&#39;').replace('<', '&lt;').replace('>', '&gt;') if readme else ""

    # Get node definitions for this package
    package_nodes = node_defs.get(github_url, {})
    node_names = list(package_nodes.keys())

    # Nodes list HTML
    nodes_html = ""
    if node_names:
        nodes_html = f'''<div class="nodes-list"><span class="nodes-label">Nodes ({len(node_names)}):</span> {", ".join(node_names[:5])}{" ..." if len(node_names) > 5 else ""}</div>'''

    # Detect media types for extensionless URLs
    media_types = {url: detect_media_type(url) for url in media_urls} if media_urls else {}

    # Generate media gallery
    gallery_html = generate_media_gallery(media_urls, media_types)
    fallback_style = "" if media_urls else 'style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 120px;"'

    # Data attributes for client-side rendering
    node_data = json.dumps(package_nodes) if package_nodes else "{}"
    media_with_types = [{"url": url, "type": media_types.get(url, "image")} for url in media_urls] if media_urls else []
    media_data = json.dumps(media_with_types)

    return f'''
                    <div class="card" data-tags="{data_tag}" data-nodes='{node_data}' data-media='{media_data}' data-stars="{stars_raw}" data-updated="{updated_at}" data-category="{category}" data-github="{github_url}" data-description="{description}" data-author="{node_author}" data-model-author="{model_author}" data-readme="{readme_escaped}" onclick="openDetail(this)">
                        <div class="card-media" {fallback_style}>
                            {gallery_html if media_urls else ""}
                        </div>
                        <div class="card-content">
                            <div class="card-header">
                                <div class="card-title">{name}</div>
                                <div class="card-stars"><i class="fas fa-star"></i> {stars}</div>
                            </div>
                            <div class="card-authors">
                                <span class="node-author">{node_author}</span> · <span class="model-author">{model_author}</span>
                            </div>
                            <div class="card-tags">
                                <span class="tag tag-io">{category}</span>
                            </div>
                            <div class="card-description">{description}</div>
                            {nodes_html}
                        </div>
                    </div>'''


def generate_html(all_nodes_with_media, node_defs, template_file):
    """Generate complete HTML page using template."""
    template = Path(template_file).read_text()

    # Collect all unique categories
    categories_in_use = set()
    for node, media, updated, readme in all_nodes_with_media:
        categories_in_use.add(node.get("category", "other-3d"))

    # Generate filter buttons
    filter_buttons = '<button class="filter-btn active" onclick="filterCards(\'all\')">All</button>\n'
    for cat_id, cat_name in CATEGORIES.items():
        if cat_id in categories_in_use:
            filter_buttons += f'                    <button class="filter-btn" onclick="filterCards(\'{cat_id}\')">{cat_name}</button>\n'

    # Generate all cards in one grid (sorted by stars)
    sorted_nodes = sorted(all_nodes_with_media, key=lambda x: int(x[0]["stars"]) if x[0]["stars"].isdigit() else 0, reverse=True)
    all_cards = "\n".join(generate_card(node, media, node_defs, updated, readme) for node, media, updated, readme in sorted_nodes)

    # Replace placeholders
    html = template.replace("<!-- FILTER_BUTTONS -->", filter_buttons)
    html = html.replace("<!-- CARDS -->", all_cards)

    return html
