"""Job array support for batch processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from hpc_runner.core.job import Job
    from hpc_runner.core.result import ArrayJobResult
    from hpc_runner.schedulers.base import BaseScheduler


@dataclass
class JobArray:
    """Represents an array job.

    Attributes:
        job: Base job specification
        start: Array start index
        end: Array end index
        step: Array step (default 1)
        max_concurrent: Max simultaneous tasks (throttling)
    """

    job: Job
    start: int = 1
    end: int = 1
    step: int = 1
    max_concurrent: int | None = None

    @property
    def range_str(self) -> str:
        """Format as scheduler range string."""
        s = f"{self.start}-{self.end}"
        if self.step != 1:
            s += f":{self.step}"
        if self.max_concurrent:
            s += f"%{self.max_concurrent}"
        return s

    @property
    def indices(self) -> Iterator[int]:
        """Iterate over array indices."""
        return iter(range(self.start, self.end + 1, self.step))

    @property
    def count(self) -> int:
        """Number of array tasks."""
        return len(range(self.start, self.end + 1, self.step))

    def submit(self, scheduler: BaseScheduler | None = None) -> ArrayJobResult:
        """Submit the array job."""
        from hpc_runner.schedulers import get_scheduler

        if scheduler is None:
            scheduler = get_scheduler()
        return scheduler.submit_array(self)
