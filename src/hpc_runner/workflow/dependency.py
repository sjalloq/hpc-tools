"""Dependency type definitions."""

from enum import Enum


class DependencyType(str, Enum):
    """Job dependency types.

    These map to scheduler-specific dependency modes:
    - SGE: -hold_jid (basic), -hold_jid_ad (array)
    - Slurm: --dependency=afterok, afterany, after, afternotok
    """

    AFTEROK = "afterok"  # Run after all dependencies complete successfully
    AFTERANY = "afterany"  # Run after all dependencies complete (success or failure)
    AFTER = "after"  # Run after all dependencies start
    AFTERNOTOK = "afternotok"  # Run after any dependency fails

    def __str__(self) -> str:
        return self.value
