"""Abstract base class for scheduler implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hpc_runner.core.job import Job
    from hpc_runner.core.job_array import JobArray
    from hpc_runner.core.result import ArrayJobResult, JobResult, JobStatus


class BaseScheduler(ABC):
    """Abstract base class for scheduler implementations.

    Each scheduler must implement:
    - submit(): Submit a job
    - submit_array(): Submit an array job
    - cancel(): Cancel a job
    - get_status(): Query job status
    - get_exit_code(): Get job exit code
    - get_output_path(): Get output file path
    - generate_script(): Generate job script
    - build_submit_command(): Build submission command
    """

    name: str  # e.g., "sge", "slurm", "local"

    @abstractmethod
    def submit(self, job: "Job", interactive: bool = False) -> "JobResult":
        """Submit a job to the scheduler.

        Args:
            job: Job specification
            interactive: Run interactively (blocking)

        Returns:
            JobResult with job ID and methods
        """

    @abstractmethod
    def submit_array(self, array: "JobArray") -> "ArrayJobResult":
        """Submit an array job."""

    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        """Cancel a job by ID."""

    @abstractmethod
    def get_status(self, job_id: str) -> "JobStatus":
        """Get current status of a job."""

    @abstractmethod
    def get_exit_code(self, job_id: str) -> int | None:
        """Get exit code of completed job."""

    @abstractmethod
    def get_output_path(self, job_id: str, stream: str) -> Path | None:
        """Get path to output file.

        Args:
            job_id: Job ID
            stream: "stdout" or "stderr"
        """

    @abstractmethod
    def generate_script(self, job: "Job") -> str:
        """Generate job script content."""

    @abstractmethod
    def build_submit_command(self, job: "Job") -> list[str]:
        """Build the submission command (e.g., qsub args)."""

    def get_scheduler_args(self, job: "Job") -> list[str]:
        """Get scheduler-specific raw args from job."""
        return getattr(job, f"{self.name}_args", [])
