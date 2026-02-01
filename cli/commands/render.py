"""Render ComfyUI workflow JSON as an image."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

# Try to import PIL, give helpful error if not installed
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Node styling
NODE_MIN_WIDTH = 200
NODE_TITLE_HEIGHT = 28
SOCKET_SPACING = 22
SOCKET_RADIUS = 6
FONT_SIZE = 11
PADDING = 12

# Colors (ComfyUI-like dark theme)
COLORS = {
    "background": (24, 24, 24),
    "node_bg": (45, 45, 45),
    "node_border": (80, 80, 80),
    "node_title_bg": (60, 60, 60),
    "text": (220, 220, 220),
    "text_dim": (150, 150, 150),
    "link": (150, 150, 200),
    "socket_input": (100, 160, 100),
    "socket_output": (160, 100, 100),
}


def render_workflow(workflow_path: Path, output_path: Path = None) -> Path:
    """Render a workflow JSON to an image."""
    if not HAS_PIL:
        console.print("[red]PIL/Pillow not installed.[/red]")
        console.print("[dim]Install with: pip install Pillow[/dim]")
        raise typer.Exit(1)

    # Load workflow
    with open(workflow_path) as f:
        workflow = json.load(f)

    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    if not nodes:
        console.print("[yellow]No nodes found in workflow[/yellow]")
        raise typer.Exit(1)

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SIZE - 2)
    except (OSError, IOError):
        font = ImageFont.load_default()
        font_small = font

    # Calculate node sizes based on inputs/outputs
    node_data = {}
    for node in nodes:
        node_id = node.get("id")
        inputs = node.get("inputs", [])
        outputs = node.get("outputs", [])

        # Use provided size or calculate based on sockets
        if "size" in node and node["size"]:
            width = max(int(node["size"][0]), NODE_MIN_WIDTH)
            height = max(int(node["size"][1]), NODE_TITLE_HEIGHT + max(len(inputs), len(outputs), 1) * SOCKET_SPACING + PADDING)
        else:
            num_sockets = max(len(inputs), len(outputs), 1)
            width = NODE_MIN_WIDTH
            height = NODE_TITLE_HEIGHT + num_sockets * SOCKET_SPACING + PADDING

        pos = node.get("pos", [0, 0])
        node_data[node_id] = {
            "pos": pos,
            "size": (width, height),
            "type": node.get("type", "Unknown"),
            "inputs": inputs,
            "outputs": outputs,
        }

    # Calculate canvas bounds
    all_x = [d["pos"][0] for d in node_data.values()]
    all_y = [d["pos"][1] for d in node_data.values()]
    all_x_end = [d["pos"][0] + d["size"][0] for d in node_data.values()]
    all_y_end = [d["pos"][1] + d["size"][1] for d in node_data.values()]

    min_x, max_x = min(all_x), max(all_x_end)
    min_y, max_y = min(all_y), max(all_y_end)

    # Add padding
    canvas_width = int(max_x - min_x + 150)
    canvas_height = int(max_y - min_y + 150)
    offset_x = -min_x + 75
    offset_y = -min_y + 75

    # Create image
    img = Image.new("RGB", (canvas_width, canvas_height), COLORS["background"])
    draw = ImageDraw.Draw(img)

    # Adjust positions with offset
    for node_id, data in node_data.items():
        data["draw_pos"] = (data["pos"][0] + offset_x, data["pos"][1] + offset_y)

    # Draw links first (behind nodes)
    # ComfyUI link format: [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
    for link in links:
        if len(link) >= 5:
            link_id, src_node_id, src_slot, dst_node_id, dst_slot = link[:5]

            if src_node_id in node_data and dst_node_id in node_data:
                src_data = node_data[src_node_id]
                dst_data = node_data[dst_node_id]

                src_pos = src_data["draw_pos"]
                dst_pos = dst_data["draw_pos"]

                # Output socket on right side of source node
                src_x = src_pos[0] + src_data["size"][0]
                src_y = src_pos[1] + NODE_TITLE_HEIGHT + src_slot * SOCKET_SPACING + SOCKET_SPACING // 2

                # Input socket on left side of destination node
                dst_x = dst_pos[0]
                dst_y = dst_pos[1] + NODE_TITLE_HEIGHT + dst_slot * SOCKET_SPACING + SOCKET_SPACING // 2

                # Draw bezier-like curve (simple version with midpoint)
                mid_x = (src_x + dst_x) / 2
                points = [
                    (src_x, src_y),
                    (src_x + 30, src_y),
                    (mid_x, (src_y + dst_y) / 2),
                    (dst_x - 30, dst_y),
                    (dst_x, dst_y)
                ]
                draw.line(points, fill=COLORS["link"], width=2)

    # Draw nodes
    for node_id, data in node_data.items():
        x, y = int(data["draw_pos"][0]), int(data["draw_pos"][1])
        width, height = int(data["size"][0]), int(data["size"][1])
        node_type = data["type"]

        # Node background with rounded corners (approximate with rectangle)
        draw.rectangle(
            [x, y, x + width, y + height],
            fill=COLORS["node_bg"],
            outline=COLORS["node_border"],
            width=1
        )

        # Title bar
        draw.rectangle(
            [x, y, x + width, y + NODE_TITLE_HEIGHT],
            fill=COLORS["node_title_bg"]
        )

        # Node title (truncate if too long)
        title = node_type if len(node_type) < 25 else node_type[:22] + "..."
        draw.text((x + PADDING, y + 7), title, fill=COLORS["text"], font=font)

        # Input sockets (left side) with labels
        for i, inp in enumerate(data["inputs"]):
            socket_y = y + NODE_TITLE_HEIGHT + i * SOCKET_SPACING + SOCKET_SPACING // 2
            draw.ellipse(
                [x - SOCKET_RADIUS, socket_y - SOCKET_RADIUS,
                 x + SOCKET_RADIUS, socket_y + SOCKET_RADIUS],
                fill=COLORS["socket_input"],
                outline=COLORS["node_border"]
            )
            # Input label
            label = inp.get("name", "") if isinstance(inp, dict) else ""
            if label:
                draw.text((x + PADDING, socket_y - 6), label[:15], fill=COLORS["text_dim"], font=font_small)

        # Output sockets (right side) with labels
        for i, out in enumerate(data["outputs"]):
            socket_y = y + NODE_TITLE_HEIGHT + i * SOCKET_SPACING + SOCKET_SPACING // 2
            draw.ellipse(
                [x + width - SOCKET_RADIUS, socket_y - SOCKET_RADIUS,
                 x + width + SOCKET_RADIUS, socket_y + SOCKET_RADIUS],
                fill=COLORS["socket_output"],
                outline=COLORS["node_border"]
            )
            # Output label (right-aligned)
            label = out.get("name", "") if isinstance(out, dict) else ""
            if label:
                label = label[:15]
                # Approximate right alignment
                draw.text((x + width - PADDING - len(label) * 5, socket_y - 6), label, fill=COLORS["text_dim"], font=font_small)

    # Determine output path
    if output_path is None:
        output_path = workflow_path.with_suffix(".png")

    img.save(output_path)
    return output_path


def render_command(
    workflow_file: str = typer.Argument(..., help="Path to workflow JSON file"),
    output: str = typer.Option(None, "-o", "--output", help="Output image path"),
):
    """Render a ComfyUI workflow JSON as an image."""
    workflow_path = Path(workflow_file)

    if not workflow_path.exists():
        console.print(f"[red]File not found: {workflow_path}[/red]")
        raise typer.Exit(1)

    output_path = Path(output) if output else None

    result_path = render_workflow(workflow_path, output_path)
    console.print(f"[green]Rendered workflow to:[/green] {result_path}")


if __name__ == "__main__":
    typer.run(render_command)
