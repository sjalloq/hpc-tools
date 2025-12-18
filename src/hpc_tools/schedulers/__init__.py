"""Scheduler registry and auto-detection."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from hpc_tools.schedulers.detection import detect_scheduler

if TYPE_CHECKING:
    from hpc_tools.schedulers.base import BaseScheduler

_SCHEDULERS: dict[str, str] = {
    "sge": "hpc_tools.schedulers.sge:SGEScheduler",
    "slurm": "hpc_tools.schedulers.slurm:SlurmScheduler",
    "pbs": "hpc_tools.schedulers.pbs:PBSScheduler",
    "local": "hpc_tools.schedulers.local:LocalScheduler",
}


def get_scheduler(name: str | None = None) -> "BaseScheduler":
    """Get scheduler instance.

    Args:
        name: Scheduler name or None to auto-detect

    Returns:
        Scheduler instance
    """
    if name is None:
        name = detect_scheduler()

    if name not in _SCHEDULERS:
        available = list(_SCHEDULERS.keys())
        raise ValueError(f"Unknown scheduler: {name}. Available: {available}")

    # Lazy import
    module_path, class_name = _SCHEDULERS[name].rsplit(":", 1)
    module = importlib.import_module(module_path)
    scheduler_class = getattr(module, class_name)

    return scheduler_class()


def register_scheduler(name: str, import_path: str) -> None:
    """Register a custom scheduler.

    Args:
        name: Scheduler name
        import_path: Import path like "mypackage.scheduler:MyScheduler"
    """
    _SCHEDULERS[name] = import_path


def list_schedulers() -> list[str]:
    """List available scheduler names."""
    return list(_SCHEDULERS.keys())


__all__ = ["get_scheduler", "register_scheduler", "list_schedulers", "detect_scheduler"]
