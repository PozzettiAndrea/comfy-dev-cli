"""Project tracking via Google Sheets."""

import os

import gspread
from google.oauth2.service_account import Credentials
from rich.console import Console
from rich.table import Table

from config import PRIVATE_DIR

console = Console()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = PRIVATE_DIR / "google.json"
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")


def get_sheet():
    """Get the Google Sheet worksheet."""
    if not CREDENTIALS_FILE.exists():
        console.print("[red]Error: Google credentials not found at private/google.json[/red]")
        raise SystemExit(1)
    if not SPREADSHEET_ID:
        console.print("[red]Error: GOOGLE_SPREADSHEET_ID not set in environment[/red]")
        raise SystemExit(1)
    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    return sheet.sheet1


def list_projects(status_filter=None, org_filter=None):
    """List all projects from the spreadsheet."""
    worksheet = get_sheet()
    data = worksheet.get_all_records()

    # Filter
    if status_filter:
        status_filter = status_filter.lower()
        data = [r for r in data if r.get('Status', '').lower() == status_filter]
    if org_filter:
        org_filter = org_filter.lower()
        data = [r for r in data if org_filter in r.get('Organisation', '').lower()]

    # Count by status
    status_counts = {}
    for row in worksheet.get_all_records():
        s = row.get('Status', 'Unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    # Display
    table = Table(title=f"Projects ({len(data)} shown)")
    table.add_column("Status", style="cyan", width=12)
    table.add_column("Name", style="bold", width=30)
    table.add_column("Organisation", width=25)
    table.add_column("Priority", width=8)
    table.add_column("What it does", width=40)

    for row in data:
        name = row.get('Name', '')
        if not name:
            continue
        status = row.get('Status', '')
        org = row.get('Organisation', '')
        priority = str(row.get('Priority', ''))
        desc = row.get('What it does', '')[:40]

        # Color status
        if status == 'Done':
            status_style = '[green]Done[/green]'
        elif status == 'NYI':
            status_style = '[yellow]NYI[/yellow]'
        elif status == 'In Progress':
            status_style = '[blue]In Progress[/blue]'
        else:
            status_style = status

        table.add_row(status_style, name, org, priority, desc)

    console.print(table)
    console.print()
    console.print("[dim]Status counts:[/dim]", end=" ")
    for s, c in sorted(status_counts.items()):
        console.print(f"[dim]{s}: {c}[/dim]", end="  ")
    console.print()


def update_status(name, new_status):
    """Update a project's status."""
    worksheet = get_sheet()
    data = worksheet.get_all_records()

    # Find the row
    for i, row in enumerate(data, start=2):  # start=2 because row 1 is header
        if row.get('Name', '').lower() == name.lower():
            # Find the Status column
            header = worksheet.row_values(1)
            status_col = header.index('Status') + 1

            worksheet.update_cell(i, status_col, new_status)
            console.print(f"[green]Updated {name} to {new_status}[/green]")
            return

    console.print(f"[red]Project '{name}' not found[/red]")


def add_project(name, org, github_url, description="", priority=""):
    """Add a new project to the spreadsheet."""
    worksheet = get_sheet()

    # Check if already exists
    data = worksheet.get_all_records()
    for row in data:
        if row.get('Name', '').lower() == name.lower():
            console.print(f"[yellow]Project '{name}' already exists[/yellow]")
            return

    # Add new row
    new_row = [name, org, 'NYI', '', github_url, priority, description, '', '']
    worksheet.append_row(new_row)
    console.print(f"[green]Added {name}[/green]")


def show_project(name):
    """Show details for a specific project."""
    worksheet = get_sheet()
    data = worksheet.get_all_records()

    for row in data:
        if row.get('Name', '').lower() == name.lower():
            console.print(f"\n[bold]{row.get('Name')}[/bold]")
            console.print(f"  Organisation: {row.get('Organisation')}")
            console.print(f"  Status: {row.get('Status')}")
            console.print(f"  Priority: {row.get('Priority')}")
            console.print(f"  What it does: {row.get('What it does')}")
            console.print(f"  GitHub (impl): {row.get('GitHub link to implementation')}")
            console.print(f"  GitHub (orig): {row.get('GitHub link to original repo')}")
            console.print(f"  Notes: {row.get('Notes')}")
            console.print(f"  More links: {row.get('More links')}")
            return

    console.print(f"[red]Project '{name}' not found[/red]")
