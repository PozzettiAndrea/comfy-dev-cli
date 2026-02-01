"""Take a screenshot of a Brev-proxied web page."""

import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console

from config import get_logger

console = Console()

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

LOCAL_URL_TEMPLATE = "http://localhost:{port}"
SCREENSHOTS_DIR = Path("/home/shadeform/screenshots")
DEFAULT_WAIT_MS = 3000


def _ensure_playwright_browsers() -> bool:
    """Check if Chromium is installed for Playwright, install if not."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        console.print("[yellow]Chromium not installed. Installing...[/yellow]")
        result = subprocess.run(
            ["playwright", "install", "chromium"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            console.print(f"[red]Failed to install Chromium: {result.stderr}[/red]")
            return False
        console.print("[green]Chromium installed[/green]")
        return True


def take_screenshot(port: int, wait_ms: int = DEFAULT_WAIT_MS, output_path: Path = None) -> int:
    """Take a screenshot of the Brev-proxied page on the given port."""
    logger = get_logger("screenshot")

    if not HAS_PLAYWRIGHT:
        console.print("[red]Playwright not installed.[/red]")
        console.print("[dim]Install with: pip install playwright && playwright install chromium[/dim]")
        return 1

    if not _ensure_playwright_browsers():
        return 1

    url = LOCAL_URL_TEMPLATE.format(port=port)

    if output_path is None:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        time_str = datetime.now().strftime("%H%M")
        output_path = SCREENSHOTS_DIR / f"screen_{time_str}.png"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Taking screenshot[/cyan]")
    console.print(f"[dim]URL: {url}[/dim]")
    console.print(f"[dim]Output: {output_path}[/dim]")
    logger.info(f"Screenshot: url={url} output={output_path} wait={wait_ms}ms")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(wait_ms)
            page.screenshot(path=str(output_path), full_page=False)
            browser.close()

        console.print(f"[green]Screenshot saved:[/green] {output_path}")
        logger.info(f"Screenshot saved to {output_path}")
        return 0

    except Exception as e:
        console.print(f"[red]Screenshot failed: {e}[/red]")
        logger.error(f"Screenshot failed: {e}")
        return 1
