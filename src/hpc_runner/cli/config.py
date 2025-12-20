"""Config command - manage configuration."""

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.syntax import Syntax

from hpc_runner.cli.main import Context, pass_context

console = Console()


@click.group()
def config_cmd() -> None:
    """Manage configuration."""
    pass


@config_cmd.command("show")
@pass_context
def show(ctx: Context) -> None:
    """Show current configuration."""
    from hpc_runner.core.config import find_config_file, load_config

    config_path = ctx.config_path or find_config_file()

    if config_path is None:
        console.print("[yellow]No configuration file found[/yellow]")
        console.print("Using default settings")
        console.print("\nSearch locations:")
        console.print("  1. ./hpc-tools.toml")
        console.print("  2. ./pyproject.toml [tool.hpc-tools]")
        console.print("  3. <git root>/hpc-tools.toml")
        console.print("  4. ~/.config/hpc-tools/config.toml")
        return

    console.print(f"[bold]Config file:[/bold] {config_path}")
    console.print()

    # Read and display the config file
    content = config_path.read_text()
    syntax = Syntax(content, "toml", theme="monokai", line_numbers=True)
    console.print(syntax)


@config_cmd.command("init")
@click.option("--global", "-g", "global_config", is_flag=True, help="Create global config")
@pass_context
def init(ctx: Context, global_config: bool) -> None:
    """Create a new configuration file."""
    if global_config:
        config_dir = Path.home() / ".config" / "hpc-tools"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.toml"
    else:
        config_path = Path.cwd() / "hpc-tools.toml"

    if config_path.exists():
        if not click.confirm(f"{config_path} already exists. Overwrite?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Write default config
    default_config = '''# hpc-tools configuration

[defaults]
# Default job settings
cpu = 1
mem = "4G"
time = "1:00:00"
# queue = "batch"

# Modules to always load
modules = []

[schedulers.sge]
# SGE-specific settings
parallel_environment = "smp"
memory_resource = "mem_free"
time_resource = "h_rt"
merge_output = true

# Tool-specific configurations
# [tools.python]
# modules = ["python/3.11"]

# Job type configurations
# [types.gpu]
# queue = "gpu"
# resources = [{name = "gpu", value = 1}]
'''

    config_path.write_text(default_config)
    console.print(f"[green]Created {config_path}[/green]")


@config_cmd.command("path")
@pass_context
def path(ctx: Context) -> None:
    """Show path to active configuration file."""
    from hpc_runner.core.config import find_config_file

    config_path = ctx.config_path or find_config_file()

    if config_path:
        console.print(str(config_path))
    else:
        console.print("[yellow]No configuration file found[/yellow]")
