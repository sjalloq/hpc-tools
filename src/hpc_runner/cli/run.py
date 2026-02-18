"""Run command - submit jobs to the scheduler."""

from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from hpc_runner.cli.main import Context, pass_context

if TYPE_CHECKING:
    from hpc_runner.core.job import Job
    from hpc_runner.schedulers.base import BaseScheduler

console = Console()


def _parse_args(args: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Split args on '--' into (scheduler_passthrough, command).

    If '--' is absent, all args are treated as the command.
    """
    args_list = list(args)
    if "--" in args_list:
        idx = args_list.index("--")
        return args_list[:idx], args_list[idx + 1 :]
    return [], args_list


@click.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    }
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
# All hpc-runner options are long-form only
@click.option("--job-name", "job_name", help="Job name")
@click.option("--cpu", type=int, help="Number of CPUs")
@click.option("--mem", help="Memory requirement (e.g., 16G)")
@click.option("--time", "time_limit", help="Time limit (e.g., 4:00:00)")
@click.option("--queue", help="Queue/partition name")
@click.option("--nodes", type=int, help="Number of nodes (MPI jobs)")
@click.option("--ntasks", type=int, help="Number of tasks (MPI jobs)")
@click.option("--directory", type=click.Path(exists=True), help="Working directory")
@click.option("--job-type", "job_type", help="Job type from config")
@click.option("--module", "modules", multiple=True, help="Modules to load (repeatable)")
@click.option("--stderr", help="Separate stderr file (default: merged)")
@click.option("--stdout", "stdout", help="Stdout file path pattern")
@click.option("--array", help="Array job specification (e.g., 1-100)")
@click.option("--depend", help="Job dependency specification")
@click.option(
    "--inherit-env/--no-inherit-env",
    "inherit_env",
    default=True,
    help="Inherit environment variables",
)
@click.option("--interactive", is_flag=True, help="Run interactively (srun/qrsh)")
@click.option("--local", is_flag=True, help="Run locally (no scheduler)")
@click.option("--dry-run", "dry_run", is_flag=True, help="Show what would be submitted")
@click.option("--wait", is_flag=True, help="Wait for job completion")
@click.option("--keep-script", "keep_script", is_flag=True, help="Keep job script for debugging")
@pass_context
def run(
    ctx: Context,
    args: tuple[str, ...],
    job_name: str | None,
    cpu: int | None,
    mem: str | None,
    time_limit: str | None,
    queue: str | None,
    nodes: int | None,
    ntasks: int | None,
    directory: str | None,
    job_type: str | None,
    modules: tuple[str, ...],
    stderr: str | None,
    stdout: str | None,
    array: str | None,
    depend: str | None,
    inherit_env: bool,
    interactive: bool,
    local: bool,
    dry_run: bool,
    wait: bool,
    keep_script: bool,
) -> None:
    """Submit a job to the scheduler.

    COMMAND is the command to execute, including any flags it needs:

    \b
        hpc run python script.py --arg value
        hpc run --interactive xterm

    Use ``--`` to pass raw scheduler arguments before the command:

    \b
        hpc run -q batch.q -l gpu=2 -- python train.py
        hpc run --cpu 4 -q batch.q -- mpirun -N 4 ./sim

    Without ``--``, everything after hpc-runner options is the command.

    TIP: For quick config-driven submissions with short options, use the
    ``submit`` command instead (e.g. ``submit -n 4 -m 16G make sim``).
    """
    import shlex

    from hpc_runner.core.job import Job
    from hpc_runner.schedulers import get_scheduler

    # Split on '--': everything before is scheduler passthrough,
    # everything after is the command.  No '--' means all command.
    scheduler_args, command_parts = _parse_args(args)

    if not command_parts:
        raise click.UsageError("Command is required")

    # Use shlex.join to preserve quoting for args with spaces/special chars
    cmd_str = shlex.join(command_parts)

    # Get scheduler
    scheduler_name = "local" if local else ctx.scheduler
    scheduler = get_scheduler(scheduler_name)

    # Create job from config or parameters
    # --job-type explicitly specifies a type, otherwise auto-detect tool from command
    if job_type:
        job = Job.from_config(command=cmd_str, job_type=job_type)
    else:
        tool_name = Path(command_parts[0]).name  # Strip path, get basename
        job = Job.from_config(tool_name, command=cmd_str)

    # Set scheduler passthrough args
    if scheduler_args:
        job.raw_args = scheduler_args

    # Apply CLI overrides
    if job_name:
        job.name = job_name
    if cpu:
        job.cpu = cpu
    if mem:
        job.mem = mem
    if time_limit:
        job.time = time_limit
    if queue:
        job.queue = queue
    if nodes:
        job.nodes = nodes
    if ntasks:
        job.tasks = ntasks
    if directory:
        job.workdir = directory
    if modules:
        job.modules = list(modules)
    if stderr:
        job.stderr = stderr
    if stdout:
        job.stdout = stdout
    if depend:
        job.dependency = depend

    # inherit_env is always set (has a default), so always apply it
    job.inherit_env = inherit_env

    # Handle array jobs
    if array:
        _handle_array_job(job, array, scheduler, dry_run, ctx.verbose)
        return

    if dry_run:
        _show_dry_run(job, scheduler, interactive=interactive)
        return

    # Submit the job
    result = scheduler.submit(job, interactive=interactive, keep_script=keep_script)

    if interactive:
        if result.returncode == 0:
            console.print("[green]Job completed successfully[/green]")
        else:
            console.print(f"[red]Job failed with exit code: {result.returncode}[/red]")
    else:
        console.print(f"Submitted job [bold cyan]{result.job_id}[/bold cyan]")

        if ctx.verbose:
            console.print(f"  Scheduler: {scheduler.name}")
            console.print(f"  Job name: {job.name}")
            console.print(f"  Command: {job.command}")
            if job.raw_args:
                console.print(f"  Passthrough args: {' '.join(job.raw_args)}")

        if wait:
            console.print("[dim]Waiting for job completion...[/dim]")
            final_status = result.wait()
            console.print(f"Job completed with status: [bold]{final_status.name}[/bold]")


def _show_dry_run(
    job: "Job",
    scheduler: "BaseScheduler",
    interactive: bool = False,
) -> None:
    """Display what would be submitted."""
    mode = "interactive" if interactive else "batch"
    lines = [
        f"[bold]Scheduler:[/bold] {scheduler.name}",
        f"[bold]Mode:[/bold] {mode}",
        f"[bold]Job name:[/bold] {job.name}",
        f"[bold]Command:[/bold] {job.command}",
    ]
    if job.raw_args:
        lines.append(f"[bold]Scheduler passthrough:[/bold] {' '.join(job.raw_args)}")
    console.print(
        Panel.fit(
            "\n".join(lines),
            title="Dry Run",
            border_style="blue",
        )
    )

    console.print("\n[bold]Generated script:[/bold]")
    if interactive:
        script = scheduler.generate_interactive_script(job, "/tmp/example_script.sh")
    else:
        script = scheduler.generate_script(job)
    syntax = Syntax(script, "bash", theme="monokai", line_numbers=True)
    console.print(syntax)


def _handle_array_job(
    job: "Job",
    array_spec: str,
    scheduler: "BaseScheduler",
    dry_run: bool,
    verbose: bool,
) -> None:
    """Handle array job submission."""
    from hpc_runner.core.job_array import JobArray

    # Parse array spec (e.g., "1-100", "1-100:10", "1-100%5")
    # Basic parsing - could be enhanced
    parts = array_spec.replace("%", ":").split(":")
    range_parts = parts[0].split("-")

    start = int(range_parts[0])
    end = int(range_parts[1]) if len(range_parts) > 1 else start
    step = int(parts[1]) if len(parts) > 1 else 1
    max_concurrent = int(parts[2]) if len(parts) > 2 else None

    array_job = JobArray(
        job=job,
        start=start,
        end=end,
        step=step,
        max_concurrent=max_concurrent,
    )

    if dry_run:
        console.print(f"[bold]Array job:[/bold] {array_job.range_str} ({array_job.count} tasks)")
        _show_dry_run(job, scheduler)
        return

    result = array_job.submit(scheduler)
    console.print(f"Submitted array job [bold cyan]{result.base_job_id}[/bold cyan]")
    console.print(f"  Tasks: {array_job.count} ({array_job.range_str})")
