"""Main CLI entry point using rich-click."""

from pathlib import Path

import rich_click as click
from rich.console import Console

# Configure rich-click
click.rich_click.SHOW_ARGUMENTS = True

# Global console for Rich output
console = Console()

# Context object to pass state between commands
class Context:
    def __init__(self) -> None:
        self.config_path: Path | None = None
        self.scheduler: str | None = None
        self.verbose: bool = False

pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
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
def cli(ctx: Context, config: Path | None, scheduler: str | None, verbose: bool) -> None:
    """HPC job submission tool.

    Submit and manage jobs across different HPC schedulers (SGE, Slurm, PBS)
    with a unified interface.

    Any unrecognized short options are passed directly to the underlying
    scheduler, allowing use of native flags like -N, -n, -q, etc.
    """
    ctx.config_path = config
    ctx.scheduler = scheduler
    ctx.verbose = verbose


# Import and register subcommands (must be after cli is defined to avoid circular imports)
from hpc_runner.cli.cancel import cancel  # noqa: E402
from hpc_runner.cli.config import config_cmd  # noqa: E402
from hpc_runner.cli.monitor import monitor  # noqa: E402
from hpc_runner.cli.run import run  # noqa: E402
from hpc_runner.cli.status import status  # noqa: E402

cli.add_command(run)
cli.add_command(status)
cli.add_command(cancel)
cli.add_command(config_cmd, name="config")
cli.add_command(monitor)


def main() -> None:
    """Entry point for console script."""
    cli()


if __name__ == "__main__":
    main()
