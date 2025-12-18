"""Type aliases for hpc-tools."""

from pathlib import Path
from typing import TypeAlias

# Path types
PathLike: TypeAlias = str | Path

# Command types
Command: TypeAlias = str | list[str]

# Resource value types
ResourceValue: TypeAlias = int | str
