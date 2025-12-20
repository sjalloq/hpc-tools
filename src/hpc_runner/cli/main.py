"""Main CLI entry point using rich-click."""

from pathlib import Path
from typing import Optional

import rich_click as click
from rich.console import Console

# Configure rich-click
click.rich_click.SHOW_ARGUMENTS = True

# Global console for Rich output
console = Console()

# Context object to pass state between commands
class Context:
    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self.scheduler: Optional[str] = None
        self.verbose: bool = False

pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option(
    "--scheduler", "-s",
    type=str,
    help="Force scheduler (sge, slurm, pbs, local)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.version_option(package_name="hpc-runner")
@pass_context
def cli(ctx: Context, config: Optional[Path], scheduler: Optional[str], verbose: bool) -> None:
    """HPC job submission tool.

    Submit and manage jobs across different HPC schedulers (SGE, Slurm, PBS)
    with a unified interface.
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
