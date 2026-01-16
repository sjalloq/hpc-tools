"""Entry point that behaves like `hpc run ...`."""

from __future__ import annotations

import sys
from typing import Final


_GLOBAL_FLAGS: Final[set[str]] = {"--config", "--scheduler", "--verbose", "-h", "--help"}


def _split_global_flags(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split argv into (global_opts, rest) for the `submit` shim.

    We only recognize the top-level CLI flags supported by `hpc`:
    --config PATH, --scheduler NAME, --verbose, -h/--help.

    Anything else is treated as part of the `run` command (including scheduler
    passthrough flags like `-q`, `-l`, etc.).
    """
    global_opts: list[str] = []
    rest: list[str] = []

    i = 0
    while i < len(argv):
        arg = argv[i]

        # Support --opt=value forms
        if arg.startswith("--config=") or arg.startswith("--scheduler="):
            global_opts.append(arg)
            i += 1
            continue

        if arg not in _GLOBAL_FLAGS:
            rest = argv[i:]
            break

        global_opts.append(arg)

        # Options with a value
        if arg in {"--config", "--scheduler"}:
            if i + 1 >= len(argv):
                # Let click surface the error message (missing value)
                break
            global_opts.append(argv[i + 1])
            i += 2
            continue

        # Flags with no value
        i += 1

    return global_opts, rest


def main() -> None:
    """Console script for `submit`.

    This is a convenience alias for `hpc run ...`, but keeps support for
    top-level flags like `submit --config ...`.
    """
    from hpc_runner.cli.main import cli

    argv = sys.argv[1:]

    # `submit --help` should show the run help (not just the group help)
    if not argv or argv == ["--help"] or argv == ["-h"]:
        cli.main(args=["run", "--help"], prog_name="submit")
        return

    global_opts, rest = _split_global_flags(argv)
    cli.main(args=[*global_opts, "run", *rest], prog_name="submit")

