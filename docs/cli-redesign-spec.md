# HPC-Runner CLI Redesign Specification

## Overview

This document specifies a redesign of the `hpc-runner` CLI to eliminate conflicts with native HPC scheduler command-line arguments while maintaining a clean, config-driven user experience.

## Design Philosophy

The primary use case for `hpc-runner` is running pre-defined workflows via TOML configuration files. Users typically configure their job parameters once and reuse them. When CLI overrides are needed, they should be intuitive and never conflict with native scheduler behavior.

### Core Principles

1. **Long options only for hpc-runner flags** - All `hpc-runner` specific options use `--long-form` only
2. **Short options pass through to scheduler** - Any `-X` style option is forwarded directly to the underlying scheduler (Slurm/SGE/PBS)
3. **Zero conflicts by design** - Users can use their familiar scheduler flags without learning new mappings
4. **Config-first approach** - CLI is for overrides, not primary configuration

## Current Problems

The existing CLI has several short options that conflict with native scheduler flags:

| hpc-runner | Slurm Conflict | SGE Conflict | Severity |
|------------|----------------|--------------|----------|
| `-N` (name) | `-N` = nodes | `-N` = job name | **Critical** |
| `-n` (dry-run) | `-n` = ntasks | - | **Critical** |
| `-c` (cpu) | `-c` = cpus-per-task | - | Medium |
| `-M` (module) | - | `-M` = mail user | Medium |
| `-t` (time) | `-t` = time | `-t` = array range | Low (same meaning for Slurm) |

Additionally, global `-c/--config` conflicts with run subcommand's `-c/--cpu`.

## New CLI Design

### Global Options (Long-Form Only)

```
hpc [GLOBAL OPTIONS] <command> [COMMAND OPTIONS]

Global Options:
  --config PATH      Path to configuration file
  --scheduler NAME   Force scheduler (sge, slurm, pbs, local)
  --verbose          Enable verbose output
  --version          Show version and exit
  --help             Show help and exit
```

### Run Command

```
hpc run [OPTIONS] [SCHEDULER_ARGS]... COMMAND...

Options (all long-form):
  --job-name TEXT    Job name (default: auto-generated from command)
  --cpu INTEGER      Number of CPUs/cores
  --mem TEXT         Memory requirement (e.g., "16G", "4096M")
  --time TEXT        Wall time limit (e.g., "4:00:00", "1-00:00:00")
  --queue TEXT       Queue/partition name
  --nodes INTEGER    Number of nodes (for MPI jobs)
  --ntasks INTEGER   Number of tasks (for MPI jobs)
  --directory PATH   Working directory (default: current)
  --job-type TEXT    Job type from config (e.g., "gpu", "mpi")
  --module TEXT      Module to load (repeatable)
  --stderr PATH      Separate stderr file (default: merged with stdout)
  --output PATH      Stdout file path pattern
  --array TEXT       Array job specification (e.g., "1-100", "1-100:10")
  --depend TEXT      Job dependency (e.g., "afterok:12345")
  --interactive      Run interactively via srun/qrsh
  --local            Run locally (no scheduler)
  --dry-run          Show what would be submitted without running
  --wait             Wait for job completion before returning
  --help             Show help and exit

Scheduler Passthrough:
  Any option starting with '-' that is not recognized above is passed
  directly to the underlying scheduler. This allows using native
  scheduler flags like:
    -N 4              Slurm: number of nodes
    -n 16             Slurm: number of tasks  
    -q batch.q        SGE: queue name
    -l gpu=2          SGE: resource request
    --gres=gpu:4      Slurm: generic resources
    --constraint=fast Slurm: node constraints
```

### Status Command

```
hpc status [OPTIONS] [JOB_ID]

Options:
  --all              Show all users' jobs
  --watch            Watch mode (refresh periodically)
  --help             Show help and exit
```

### Cancel Command

```
hpc cancel [OPTIONS] JOB_ID

Options:
  --force            Cancel without confirmation
  --help             Show help and exit
```

### Config Command

```
hpc config <subcommand>

Subcommands:
  show               Show current configuration
  init               Create new configuration file
  path               Show path to active config file

Options for 'init':
  --global           Create in ~/.config/hpc-tools/
```

## Usage Examples

### Config-Driven Workflows (Primary Use Case)

```bash
# Use pre-configured job type
hpc run --job-type gpu "python train.py --epochs 100"

# Override specific parameters
hpc run --job-type gpu --time 8:00:00 "python train.py"

# Simple job with defaults from config
hpc run "make -j8 all"
```

### Direct Parameter Specification

```bash
# All hpc-runner options (long-form)
hpc run --cpu 4 --mem 16G --time 2:00:00 --queue batch "python script.py"

# With job name and modules
hpc run --job-name "training-run" --module cuda/12.0 --module python/3.11 "python train.py"
```

### Scheduler Passthrough (Power Users)

```bash
# Slurm native flags pass through
hpc run -N 4 -n 16 --mem 64G "mpirun ./simulation"
#       ^^^^^ passed to sbatch directly

# SGE native flags pass through
hpc run -pe mpi 16 -l exclusive=true "mpirun ./simulation"
#       ^^^^^^^^^^^^^^^^^^^^^^^^^ passed to qsub directly

# Mix hpc-runner options with native flags
hpc run --cpu 4 --mem 16G -l scratch=100G "process_data.sh"
#       ^^^^^^^^^^^^^^^ hpc-runner   ^^^^^^^^^^^^^^ SGE passthrough

# Complex Slurm job with native options
hpc run --job-type mpi --gres=gpu:4 --constraint=a100 "train_distributed.py"
#                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Slurm passthrough
```

### Array Jobs

```bash
# Using hpc-runner abstraction
hpc run --array 1-100 --cpu 2 "python process.py \$TASK_ID"

# Or native Slurm
hpc run --cpu 2 -a 1-100%10 "python process.py \$SLURM_ARRAY_TASK_ID"
#               ^^^^^^^^^^ passed to sbatch (with throttle)
```

### Interactive and Local Execution

```bash
# Interactive session on cluster
hpc run --interactive --cpu 4 --mem 8G "bash"

# Local execution (testing without scheduler)
hpc run --local --cpu 4 "make test"

# Dry run to see generated script
hpc run --dry-run --cpu 8 --mem 32G "python train.py"
```

## Implementation Details

### File: `src/hpc_runner/cli/main.py`

```python
"""Main CLI entry point using rich-click."""

from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console

click.rich_click.SHOW_ARGUMENTS = True

console = Console()


class Context:
    """Context object passed between commands."""
    
    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self.scheduler: Optional[str] = None
        self.verbose: bool = False


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--scheduler",
    type=str,
    help="Force scheduler (sge, slurm, pbs, local)",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output",
)
@click.version_option(package_name="hpc-runner")
@pass_context
def cli(ctx: Context, config: Optional[Path], scheduler: Optional[str], verbose: bool) -> None:
    """HPC job submission tool.

    Submit and manage jobs across different HPC schedulers (SGE, Slurm, PBS)
    with a unified interface.
    
    Any unrecognized short options are passed directly to the underlying
    scheduler, allowing use of native flags like -N, -n, -q, etc.
    """
    ctx.config_path = config
    ctx.scheduler = scheduler
    ctx.verbose = verbose


# Import and register subcommands
from hpc_runner.cli.run import run
from hpc_runner.cli.status import status
from hpc_runner.cli.cancel import cancel
from hpc_runner.cli.config import config_cmd

cli.add_command(run)
cli.add_command(status)
cli.add_command(cancel)
cli.add_command(config_cmd, name="config")


def main() -> None:
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()
```

### File: `src/hpc_runner/cli/run.py`

```python
"""Run command - submit jobs to the scheduler."""

import shlex
from typing import List, Optional, Tuple

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from hpc_runner.cli.main import Context, pass_context

console = Console()


class SchedulerArgsType(click.ParamType):
    """Custom parameter type that captures unknown options for passthrough."""
    
    name = "scheduler_args"
    
    def convert(self, value, param, ctx):
        return value


@click.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": True,
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
@click.option("--output", help="Stdout file path pattern")
@click.option("--array", help="Array job specification (e.g., 1-100)")
@click.option("--depend", help="Job dependency specification")
@click.option("--interactive", is_flag=True, help="Run interactively (srun/qrsh)")
@click.option("--local", is_flag=True, help="Run locally (no scheduler)")
@click.option("--dry-run", "dry_run", is_flag=True, help="Show what would be submitted")
@click.option("--wait", is_flag=True, help="Wait for job completion")
@pass_context
def run(
    ctx: Context,
    args: Tuple[str, ...],
    job_name: Optional[str],
    cpu: Optional[int],
    mem: Optional[str],
    time_limit: Optional[str],
    queue: Optional[str],
    nodes: Optional[int],
    ntasks: Optional[int],
    directory: Optional[str],
    job_type: Optional[str],
    modules: Tuple[str, ...],
    stderr: Optional[str],
    output: Optional[str],
    array: Optional[str],
    depend: Optional[str],
    interactive: bool,
    local: bool,
    dry_run: bool,
    wait: bool,
) -> None:
    """Submit a job to the scheduler.

    COMMAND is the command to execute. Use quotes for complex commands:

    \b
        hpc run "make -j8 all"
        hpc run python script.py --arg value

    Any unrecognized options starting with '-' are passed directly to the
    underlying scheduler. This allows using native flags:

    \b
        hpc run -N 4 -n 16 "mpirun ./sim"     # Slurm nodes/tasks
        hpc run -q batch.q -l gpu=2 "train"   # SGE queue/resources
    """
    from hpc_runner.core.job import Job
    from hpc_runner.schedulers import get_scheduler

    # Parse args into command and scheduler passthrough args
    command_parts, scheduler_args = _parse_args(args)
    
    if not command_parts:
        raise click.UsageError("Command is required")
    
    cmd_str = " ".join(command_parts)

    # Get scheduler
    scheduler_name = "local" if local else ctx.scheduler
    scheduler = get_scheduler(scheduler_name)

    # Create job from config or parameters
    if job_type:
        job = Job.from_config(job_type, command=cmd_str)
    else:
        job = Job(command=cmd_str)

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
    if output:
        job.stdout = output
    if depend:
        job.dependency = depend
    
    # Add scheduler passthrough args
    if scheduler_args:
        job.raw_args = scheduler_args
        if ctx.verbose:
            console.print(f"[dim]Scheduler passthrough: {' '.join(scheduler_args)}[/dim]")

    # Handle array jobs
    if array:
        _handle_array_job(job, array, scheduler, dry_run, ctx.verbose)
        return

    if dry_run:
        _show_dry_run(job, scheduler, scheduler_args)
        return

    # Submit the job
    result = scheduler.submit(job, interactive=interactive)

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

        if wait:
            console.print("[dim]Waiting for job completion...[/dim]")
            final_status = result.wait()
            console.print(f"Job completed with status: [bold]{final_status.name}[/bold]")


def _parse_args(args: Tuple[str, ...]) -> Tuple[List[str], List[str]]:
    """Parse args into command parts and scheduler passthrough args.
    
    Scheduler args are any args that:
    - Start with '-' and are not recognized hpc-runner options
    - Include their values (e.g., "-N 4" becomes ["-N", "4"])
    
    The command is everything after the first non-option arg or after '--'.
    
    Args:
        args: Raw arguments from click
        
    Returns:
        Tuple of (command_parts, scheduler_args)
    """
    command_parts: List[str] = []
    scheduler_args: List[str] = []
    
    args_list = list(args)
    i = 0
    in_command = False
    
    while i < len(args_list):
        arg = args_list[i]
        
        # '--' signals end of options
        if arg == '--':
            in_command = True
            i += 1
            continue
        
        if in_command:
            command_parts.append(arg)
            i += 1
            continue
            
        # Check if this looks like an option
        if arg.startswith('-'):
            # This is a scheduler passthrough option
            scheduler_args.append(arg)
            
            # Check if next arg is the value (not another option)
            if i + 1 < len(args_list) and not args_list[i + 1].startswith('-'):
                # Handle special case: is this a flag or does it take a value?
                # Heuristic: if next arg doesn't start with '-', treat as value
                # unless the current arg uses '=' syntax
                if '=' not in arg:
                    i += 1
                    scheduler_args.append(args_list[i])
            i += 1
        else:
            # First non-option arg starts the command
            in_command = True
            command_parts.append(arg)
            i += 1
    
    return command_parts, scheduler_args


def _show_dry_run(job: "Job", scheduler, scheduler_args: List[str]) -> None:
    """Display what would be submitted."""
    from hpc_runner.schedulers.base import BaseScheduler

    console.print(Panel.fit(
        f"[bold]Scheduler:[/bold] {scheduler.name}\n"
        f"[bold]Job name:[/bold] {job.name}\n"
        f"[bold]Command:[/bold] {job.command}",
        title="Dry Run",
        border_style="blue"
    ))
    
    if scheduler_args:
        console.print(f"\n[bold]Scheduler passthrough args:[/bold] {' '.join(scheduler_args)}")

    console.print("\n[bold]Generated script:[/bold]")
    script = scheduler.generate_script(job)
    syntax = Syntax(script, "bash", theme="monokai", line_numbers=True)
    console.print(syntax)


def _handle_array_job(job, array_spec: str, scheduler, dry_run: bool, verbose: bool) -> None:
    """Handle array job submission."""
    from hpc_runner.core.job_array import JobArray
    
    # Parse array spec (e.g., "1-100", "1-100:10", "1-100%5")
    # Basic parsing - could be enhanced
    parts = array_spec.replace('%', ':').split(':')
    range_parts = parts[0].split('-')
    
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
        _show_dry_run(job, scheduler, [])
        return
    
    result = array_job.submit(scheduler)
    console.print(f"Submitted array job [bold cyan]{result.base_job_id}[/bold cyan]")
    console.print(f"  Tasks: {array_job.count} ({array_job.range_str})")
```

### File: `src/hpc_runner/core/job.py` (Updates)

Add these fields to the Job dataclass if not present:

```python
@dataclass
class Job:
    """Represents a job to be submitted."""
    
    command: str | list[str]
    name: str | None = None
    cpu: int | None = None
    mem: str | None = None
    time: str | None = None
    queue: str | None = None
    nodes: int | None = None
    tasks: int | None = None  # Was 'ntasks' - standardize naming
    resources: ResourceSet = field(default_factory=ResourceSet)
    modules: list[str] = field(default_factory=list)
    modules_path: list[str] = field(default_factory=list)
    inherit_env: bool = True
    workdir: Path | str | None = None
    stdout: str | None = None
    stderr: str | None = None  # None = merge with stdout
    dependency: str | None = None  # Dependency specification
    
    # Raw passthrough arguments
    raw_args: list[str] = field(default_factory=list)
    sge_args: list[str] = field(default_factory=list)
    slurm_args: list[str] = field(default_factory=list)
    pbs_args: list[str] = field(default_factory=list)

    # ... rest of implementation
```

### Scheduler Integration

Each scheduler implementation should handle `raw_args` in its submit command building:

```python
# In schedulers/sge/scheduler.py
def build_submit_command(self, job: Job) -> list[str]:
    cmd = ["qsub", "-cwd"]
    
    # Add abstracted options
    if job.queue:
        cmd.extend(["-q", job.queue])
    if job.cpu:
        cmd.extend(["-pe", self.config.parallel_environment, str(job.cpu)])
    # ... etc
    
    # Add raw passthrough args (these go directly to qsub)
    cmd.extend(job.raw_args)
    cmd.extend(job.sge_args)
    
    return cmd

# In schedulers/slurm/scheduler.py  
def build_submit_command(self, job: Job) -> list[str]:
    cmd = ["sbatch"]
    
    # Add abstracted options
    if job.cpu:
        cmd.append(f"--cpus-per-task={job.cpu}")
    if job.nodes:
        cmd.append(f"--nodes={job.nodes}")
    # ... etc
    
    # Add raw passthrough args (these go directly to sbatch)
    cmd.extend(job.raw_args)
    cmd.extend(job.slurm_args)
    
    return cmd
```

## Testing Considerations

### Test Cases for Argument Parsing

```python
def test_parse_simple_command():
    args = ("python", "script.py")
    cmd, sched = _parse_args(args)
    assert cmd == ["python", "script.py"]
    assert sched == []

def test_parse_with_scheduler_flags():
    args = ("-N", "4", "-n", "16", "mpirun", "./sim")
    cmd, sched = _parse_args(args)
    assert cmd == ["mpirun", "./sim"]
    assert sched == ["-N", "4", "-n", "16"]

def test_parse_with_equals_syntax():
    args = ("--gres=gpu:2", "python", "train.py")
    cmd, sched = _parse_args(args)
    assert cmd == ["python", "train.py"]
    assert sched == ["--gres=gpu:2"]

def test_parse_with_double_dash():
    args = ("-N", "4", "--", "python", "-c", "print('hello')")
    cmd, sched = _parse_args(args)
    assert cmd == ["python", "-c", "print('hello')"]
    assert sched == ["-N", "4"]

def test_parse_mixed_options():
    # This tests the real-world case
    args = ("-l", "gpu=2", "-q", "batch.q", "python", "train.py", "--epochs", "100")
    cmd, sched = _parse_args(args)
    assert cmd == ["python", "train.py", "--epochs", "100"]
    assert sched == ["-l", "gpu=2", "-q", "batch.q"]
```

### Integration Tests

```python
def test_dry_run_shows_passthrough():
    """Verify passthrough args appear in dry-run output."""
    result = runner.invoke(cli, [
        "run", "--dry-run", "-N", "4", "-n", "16", "mpirun", "./sim"
    ])
    assert "-N 4" in result.output or "--nodes=4" in result.output
    assert result.exit_code == 0

def test_passthrough_in_submit_command():
    """Verify passthrough args are included in actual submission."""
    # Mock subprocess.run to capture the command
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="Submitted job 12345")
        result = runner.invoke(cli, [
            "run", "-l", "scratch=100G", "process.sh"
        ])
    
    call_args = mock_run.call_args[0][0]
    assert "-l" in call_args
    assert "scratch=100G" in call_args
```

## Documentation Updates

### README.md Section

Add this to the README:

```markdown
## CLI Usage

### Basic Usage

```bash
# Submit a job using config defaults
hpc run "make all"

# Override specific parameters  
hpc run --cpu 4 --mem 16G --time 2:00:00 "python train.py"

# Use a pre-configured job type
hpc run --job-type gpu "python train.py"
```

### Native Scheduler Options

Any short option (`-X`) not recognized by hpc-runner is passed directly 
to the underlying scheduler. This means you can use familiar Slurm or 
SGE flags without learning new syntax:

```bash
# Slurm users can use native flags
hpc run -N 4 -n 16 --gres=gpu:4 "mpirun ./simulation"

# SGE users can use native flags  
hpc run -pe mpi 16 -l exclusive=true "mpirun ./simulation"
```

### Long vs Short Options

| hpc-runner (long) | Use for |
|-------------------|---------|
| `--cpu` | CPU count (abstracted) |
| `--mem` | Memory (abstracted) |
| `--time` | Wall time (abstracted) |
| `--queue` | Queue/partition (abstracted) |
| `--nodes` | Node count (abstracted) |
| `--job-name` | Job name |
| `--job-type` | Config job type |
| `--dry-run` | Preview submission |

| Passthrough (short) | Goes to |
|---------------------|---------|
| `-N 4` | Slurm: nodes |
| `-n 16` | Slurm: tasks |
| `-q batch.q` | SGE: queue |
| `-l resource=val` | SGE: resources |
| `-a 1-100` | Slurm: array |
| Any other `-X` | Scheduler directly |
```

## Migration Notes

### For Existing Users

If you were using the old short options, update your scripts:

| Old | New |
|-----|-----|
| `hpc run -N jobname` | `hpc run --job-name jobname` |
| `hpc run -c 4` | `hpc run --cpu 4` |
| `hpc run -n` (dry-run) | `hpc run --dry-run` |
| `hpc run -M module` | `hpc run --module module` |
| `hpc -c config.toml` | `hpc --config config.toml` |

### Behavior Changes

1. **Short options now pass through** - If you were accidentally using `-N` thinking it set the job name, it will now be passed to Slurm as the number of nodes. Use `--job-name` instead.

2. **No more conflicts** - You can now freely use native scheduler options without worrying about hpc-runner intercepting them.

## Checklist for Implementation

- [ ] Update `cli/main.py` - Remove all short options from global group
- [ ] Update `cli/run.py` - Remove all short options, add passthrough parsing
- [ ] Update `cli/status.py` - Remove short options (keep `--all`, `--watch`)
- [ ] Update `cli/cancel.py` - Remove short options (keep `--force`)
- [ ] Update `cli/config.py` - Remove short options (keep `--global`)
- [ ] Update `core/job.py` - Add `dependency` field, ensure `raw_args` handling
- [ ] Update scheduler implementations - Include `raw_args` in submit commands
- [ ] Add tests for argument parsing edge cases
- [ ] Update README and help text
- [ ] Update CLAUDE.md with new CLI examples
