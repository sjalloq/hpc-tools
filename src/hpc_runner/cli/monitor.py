"""CLI command for launching the interactive job monitor."""

import rich_click as click


@click.command()
@click.option(
    "--refresh",
    "-r",
    default=10,
    type=int,
    help="Auto-refresh interval in seconds",
)
def monitor(refresh: int) -> None:
    """Launch interactive job monitor TUI.

    Opens a terminal UI for monitoring HPC jobs across schedulers.
    Shows active and completed jobs with filtering and search.

    \b
    Keyboard shortcuts:
      q      Quit
      r      Manual refresh
      u      Toggle user filter (me/all)
      Tab    Switch tabs
    """
    from hpc_runner.tui import HpcMonitorApp

    app = HpcMonitorApp(refresh_interval=refresh)
    app.run()
