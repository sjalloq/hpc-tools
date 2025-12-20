"""Job model for HPC job submission."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hpc_runner.core.resources import ResourceSet

if TYPE_CHECKING:
    from hpc_runner.core.result import JobResult
    from hpc_runner.schedulers.base import BaseScheduler


@dataclass
class Job:
    """Represents a job to be submitted.

    Attributes:
        command: The command to execute (string or list)
        name: Job name (auto-generated if not provided)
        cpu: Number of CPUs/cores/slots
        mem: Memory requirement (e.g., "16G", "4096M")
        time: Wall time limit (e.g., "4:00:00", "1-00:00:00")
        queue: Queue/partition name
        nodes: Number of nodes (for MPI jobs)
        tasks: Number of tasks (for MPI jobs)
        resources: Additional resource requests
        modules: Environment modules to load
        modules_path: Additional module paths
        inherit_env: Inherit current environment
        workdir: Working directory (default: current)
        stdout: Stdout file path (supports templates)
        stderr: Stderr file path (None = merge with stdout)
        raw_args: Raw scheduler arguments (passthrough)
        sge_args: SGE-specific raw arguments
        slurm_args: Slurm-specific raw arguments
        pbs_args: PBS-specific raw arguments
    """

    command: str | list[str]
    name: str | None = None
    cpu: int | None = None
    mem: str | None = None
    time: str | None = None
    queue: str | None = None
    nodes: int | None = None
    tasks: int | None = None
    resources: ResourceSet = field(default_factory=ResourceSet)
    modules: list[str] = field(default_factory=list)
    modules_path: list[str] = field(default_factory=list)
    inherit_env: bool = True
    workdir: Path | str | None = None
    stdout: str | None = None
    stderr: str | None = None  # None = merge with stdout

    # Raw passthrough arguments
    raw_args: list[str] = field(default_factory=list)
    sge_args: list[str] = field(default_factory=list)
    slurm_args: list[str] = field(default_factory=list)
    pbs_args: list[str] = field(default_factory=list)

    # Dependency management
    dependencies: list[JobResult] = field(default_factory=list)
    dependency_type: str = "afterok"  # afterok, afterany, after, afternotok

    def __post_init__(self) -> None:
        if self.name is None:
            self.name = self._generate_name()
        if isinstance(self.command, list):
            self.command = " ".join(self.command)
        if self.workdir is not None and not isinstance(self.workdir, Path):
            self.workdir = Path(self.workdir)

    def _generate_name(self) -> str:
        """Generate job name from command."""
        user = os.environ.get("USER", "user")
        # Extract first word of command, strip path
        cmd_str = self.command if isinstance(self.command, str) else self.command[0]
        cmd = cmd_str.split()[0]
        cmd = Path(cmd).name
        cmd = re.sub(r"[^a-zA-Z0-9_-]", "_", cmd)
        return f"{user}_{cmd}"

    def submit(self, scheduler: BaseScheduler | None = None) -> JobResult:
        """Submit the job.

        Args:
            scheduler: Scheduler to use. Auto-detects if None.

        Returns:
            JobResult with job ID and status methods
        """
        from hpc_runner.schedulers import get_scheduler

        if scheduler is None:
            scheduler = get_scheduler()
        return scheduler.submit(self)

    def after(self, *jobs: JobResult, type: str = "afterok") -> Job:
        """Add dependency on other jobs.

        Args:
            jobs: Jobs this job depends on
            type: Dependency type (afterok, afterany, after, afternotok)
        """
        self.dependencies.extend(jobs)
        self.dependency_type = type
        return self

    @classmethod
    def from_config(
        cls,
        tool_or_type: str,
        command: str | None = None,
        **overrides: Any,
    ) -> Job:
        """Create job from configuration.

        Args:
            tool_or_type: Tool name or job type from config
            command: Override command (uses config template if None)
            **overrides: Override any job parameters
        """
        from hpc_runner.core.config import load_config

        config = load_config()
        job_config = config.get_job_config(tool_or_type)

        if command:
            job_config["command"] = command
        job_config.update(overrides)

        # Handle resources specially
        if "resources" in job_config and isinstance(job_config["resources"], list):
            resource_set = ResourceSet()
            for r in job_config["resources"]:
                resource_set.add(r["name"], r["value"])
            job_config["resources"] = resource_set

        return cls(**job_config)

    @property
    def merge_output(self) -> bool:
        """Whether stderr should be merged with stdout."""
        return self.stderr is None
