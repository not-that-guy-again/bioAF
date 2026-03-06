"""Rich console output utilities for bioAF CLI."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

console = Console()


def print_success(message: str) -> None:
    """Print a success message with a green checkmark."""
    console.print(f"  [green][bold]OK[/bold][/green]  {message}")


def print_error(message: str) -> None:
    """Print an error message with a red X."""
    console.print(f"  [red][bold]FAIL[/bold][/red]  {message}")


def print_warning(message: str) -> None:
    """Print a warning message with a yellow indicator."""
    console.print(f"  [yellow][bold]WARN[/bold][/yellow]  {message}")


def print_step(message: str) -> None:
    """Print a step description (neutral)."""
    console.print(f"  [blue][bold]....[/bold][/blue]  {message}")


def create_progress_display() -> Progress:
    """Create a Rich progress display with spinner and text columns."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=False,
    )


def print_resource_table(title: str, resources: list[dict[str, str]]) -> None:
    """Print a table of resources with name and status columns."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Resource", style="dim")
    table.add_column("Status")
    for resource in resources:
        table.add_row(resource["name"], resource["status"])
    console.print(table)


def print_panel(title: str, content: str, style: str = "green") -> None:
    """Print content inside a styled panel."""
    console.print(Panel(content, title=title, border_style=style))
