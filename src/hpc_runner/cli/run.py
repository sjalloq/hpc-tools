"""Run command - submit jobs to the scheduler."""

from typing import Optional, Tuple

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from hpc_runner.cli.main import Context, pass_context

console = Console()


@click.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--name", "-N", help="Job name")
@click.option("--cpu", "-c", type=int, help="Number of CPUs")
@click.option("--mem", "-m", help="Memory requirement (e.g., 16G)")
@click.option("--time", "-t", help="Time limit (e.g., 4:00:00)")
@click.option("--queue", "-q", help="Queue/partition name")
@click.option("--interactive", "-I", is_flag=True, help="Run interactively (blocking)")
@click.option("--local", "-L", is_flag=True, help="Run locally (no scheduler)")
@click.option("--type", "-T", "job_type", help="Job type from config")
@click.option("--module", "-M", multiple=True, help="Modules to load (can be repeated)")
@click.option("--raw", "-R", multiple=True, help="Raw scheduler args (can be repeated)")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be submitted")
@click.option("--stderr", "-e", help="Separate stderr file (default: merged with stdout)")
@pass_context
def run(
    ctx: Context,
    command: Tuple[str, ...],
    name: Optional[str],
    cpu: Optional[int],
    mem: Optional[str],
    time: Optional[str],
    queue: Optional[str],
    interactive: bool,
    local: bool,
    job_type: Optional[str],
    module: Tuple[str, ...],
    raw: Tuple[str, ...],
    dry_run: bool,
    stderr: Optional[str],
) -> None:
    """Submit a job to the scheduler.

    COMMAND is the command to execute. Use quotes for complex commands:

        hpc run "make -j8 all"

        hpc run python script.py --arg value
    """
    from hpc_runner.core.job import Job
    from hpc_runner.schedulers import get_scheduler

    # Get scheduler
    scheduler_name = "local" if local else ctx.scheduler
    scheduler = get_scheduler(scheduler_name)

    # Build command string
    cmd_str = " ".join(command)

    # Create job from config or parameters
    if job_type:
        job = Job.from_config(job_type, command=cmd_str)
    else:
        job = Job(command=cmd_str)

    # Override with CLI arguments
    if name:
        job.name = name
    if cpu:
        job.cpu = cpu
    if mem:
        job.mem = mem
    if time:
        job.time = time
    if queue:
        job.queue = queue
    if module:
        job.modules = list(module)
    if raw:
        job.raw_args = list(raw)
    if stderr:
        job.stderr = stderr

    if dry_run:
        _show_dry_run(job, scheduler)
        return

    # Submit
    result = scheduler.submit(job, interactive=interactive)

    if interactive:
        if result.returncode == 0:
            console.print(f"[green]Job completed successfully[/green]")
        else:
            console.print(f"[red]Job failed with exit code: {result.returncode}[/red]")
    else:
        console.print(f"Submitted job [bold cyan]{result.job_id}[/bold cyan]")
        if ctx.verbose:
            console.print(f"  Scheduler: {scheduler.name}")
            console.print(f"  Job name: {job.name}")
            console.print(f"  Command: {job.command}")


def _show_dry_run(job: "Job", scheduler: "BaseScheduler") -> None:
    """Display what would be submitted."""
    from hpc_runner.schedulers.base import BaseScheduler

    console.print(Panel.fit("[bold]Dry Run[/bold]", border_style="yellow"))
    console.print(f"[bold]Scheduler:[/bold] {scheduler.name}")
    console.print(f"[bold]Job Name:[/bold] {job.name}")
    console.print(f"[bold]Command:[/bold] {job.command}")

    if job.cpu:
        console.print(f"[bold]CPU:[/bold] {job.cpu}")
    if job.mem:
        console.print(f"[bold]Memory:[/bold] {job.mem}")
    if job.time:
        console.print(f"[bold]Time:[/bold] {job.time}")
    if job.queue:
        console.print(f"[bold]Queue:[/bold] {job.queue}")
    if job.modules:
        console.print(f"[bold]Modules:[/bold] {', '.join(job.modules)}")
    if job.merge_output:
        console.print(f"[bold]Output:[/bold] merged (stdout only)")
    else:
        console.print(f"[bold]Stderr:[/bold] {job.stderr}")

    console.print()
    console.print("[bold]Generated Script:[/bold]")
    script = scheduler.generate_script(job)
    syntax = Syntax(script, "bash", theme="monokai", line_numbers=True)
    console.print(syntax)
