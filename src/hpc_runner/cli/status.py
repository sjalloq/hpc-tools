"""Status command - check job status."""

from typing import Optional

import rich_click as click
from rich.console import Console
from rich.table import Table

from hpc_runner.cli.main import Context, pass_context

console = Console()


@click.command()
@click.argument("job_id", required=False)
@click.option("--all", "-a", "all_users", is_flag=True, help="Show all users' jobs")
@click.option("--watch", "-w", is_flag=True, help="Watch mode (refresh periodically)")
@pass_context
def status(
    ctx: Context,
    job_id: Optional[str],
    all_users: bool,
    watch: bool,
) -> None:
    """Check job status.

    If JOB_ID is provided, show status of that specific job.
    Otherwise, list all your jobs.
    """
    from hpc_runner.schedulers import get_scheduler

    scheduler = get_scheduler(ctx.scheduler)

    if job_id:
        # Show specific job status
        status = scheduler.get_status(job_id)
        exit_code = scheduler.get_exit_code(job_id)

        table = Table(title=f"Job {job_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Status", _status_style(status.name))
        if exit_code is not None:
            table.add_row("Exit Code", str(exit_code))

        console.print(table)
    else:
        # List all jobs (not implemented for all schedulers)
        console.print("[yellow]Listing all jobs requires scheduler-specific implementation[/yellow]")
        console.print("Use 'hpc status <job_id>' to check a specific job")


def _status_style(status: str) -> str:
    """Apply color to status string."""
    colors = {
        "PENDING": "[yellow]PENDING[/yellow]",
        "RUNNING": "[blue]RUNNING[/blue]",
        "COMPLETED": "[green]COMPLETED[/green]",
        "FAILED": "[red]FAILED[/red]",
        "CANCELLED": "[magenta]CANCELLED[/magenta]",
        "TIMEOUT": "[red]TIMEOUT[/red]",
        "UNKNOWN": "[dim]UNKNOWN[/dim]",
    }
    return colors.get(status, status)
