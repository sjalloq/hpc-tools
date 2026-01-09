"""Job model - pure data container with no scheduler knowledge."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Iterator

from hpc_runner.core.descriptors import JobAttribute
from hpc_runner.core.resources import ResourceSet

if TYPE_CHECKING:
    from hpc_runner.core.result import JobResult
    from hpc_runner.schedulers.base import BaseScheduler


class Job:
    """HPC job specification.

    This is a pure data container. It has no knowledge of any specific
    scheduler's syntax. Rendering to scheduler-specific formats is handled
    by the scheduler classes.

    Attributes are defined using JobAttribute descriptors, which enables:
    - Clean attribute access: job.name, job.cpu, etc.
    - Iteration over set attributes via iter_attributes()
    - Class-level introspection: Job.name returns the descriptor

    Example:
        job = Job(
            command="python train.py",
            name="training_run",
            cpu=4,
            mem="16G",
            time="4:00:00",
        )

        # Direct access
        print(job.name)  # "training_run"
        print(job.cpu)   # 4

        # Iterate over set attributes
        for attr, value in job.iter_attributes():
            print(f"{attr}={value}")
    """

    # =========================================================================
    # Attribute Descriptors
    # =========================================================================

    # Job identification
    name = JobAttribute[str]("name")

    # Resource requests
    cpu = JobAttribute[int]("cpu")
    mem = JobAttribute[str]("mem")
    time = JobAttribute[str]("time")

    # Scheduling
    queue = JobAttribute[str]("queue")
    priority = JobAttribute[int]("priority")

    # MPI/Multi-node jobs (primarily Slurm, but kept for compatibility)
    nodes = JobAttribute[int]("nodes")
    tasks = JobAttribute[int]("tasks")

    # Output handling
    stdout = JobAttribute[str]("stdout")
    stderr = JobAttribute[str]("stderr")

    # Environment
    inherit_env = JobAttribute[bool]("inherit_env", default=True)
    workdir = JobAttribute[str]("workdir")
    shell = JobAttribute[str]("shell", default="/bin/bash")
    venv = JobAttribute[str]("venv")  # Virtual environment path

    # Working directory behavior
    use_cwd = JobAttribute[bool]("use_cwd", default=True)

    # Note: 'dependency' is NOT a descriptor - it's handled specially by schedulers
    # because it involves both string form (CLI) and programmatic form (Job.after())

    # =========================================================================
    # Attribute Registry - Order matters for directive generation
    # =========================================================================

    RENDERABLE_ATTRIBUTES: list[str] = [
        "shell",
        "use_cwd",
        "inherit_env",
        "name",
        "cpu",
        "mem",
        "time",
        "queue",
        "priority",
        "nodes",
        "tasks",
        "stdout",
        "stderr",
    ]

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        command: str | list[str],
        *,
        name: str | None = None,
        cpu: int | None = None,
        mem: str | None = None,
        time: str | None = None,
        queue: str | None = None,
        priority: int | None = None,
        nodes: int | None = None,
        tasks: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        inherit_env: bool = True,
        workdir: str | None = None,
        shell: str = "/bin/bash",
        use_cwd: bool = True,
        venv: str | None = None,
        env_vars: dict[str, str] | None = None,
        modules: list[str] | None = None,
        modules_path: list[str] | None = None,
        resources: ResourceSet | None = None,
        raw_args: list[str] | None = None,
        sge_args: list[str] | None = None,
        slurm_args: list[str] | None = None,
        pbs_args: list[str] | None = None,
        dependency: str | None = None,
    ):
        # Command handling
        if isinstance(command, list):
            self.command = " ".join(command)
        else:
            self.command = command

        # Set descriptor-based attributes
        self.name = name or self._generate_name()
        self.cpu = cpu
        self.mem = mem
        self.time = time
        self.queue = queue
        self.priority = priority
        self.nodes = nodes
        self.tasks = tasks
        self.stdout = stdout
        self.stderr = stderr
        self.inherit_env = inherit_env
        self.workdir = workdir
        self.shell = shell
        self.use_cwd = use_cwd

        # Virtual environment - auto-capture from VIRTUAL_ENV if not specified
        if venv is None:
            venv = os.environ.get("VIRTUAL_ENV")
        self.venv = venv

        # Non-descriptor attributes
        self.env_vars: dict[str, str] = env_vars or {}
        self.modules: list[str] = modules or []
        self.modules_path: list[str] = modules_path or []
        self.resources: ResourceSet = resources or ResourceSet()
        self.raw_args: list[str] = raw_args or []
        self.sge_args: list[str] = sge_args or []
        self.slurm_args: list[str] = slurm_args or []
        self.pbs_args: list[str] = pbs_args or []
        self.dependency: str | None = dependency

        # Programmatic dependencies (from .after() method)
        self.dependencies: list[JobResult] = []
        self.dependency_type: str = "afterok"

    # =========================================================================
    # Submission API
    # =========================================================================

    def submit(self, scheduler: "BaseScheduler | None" = None) -> "JobResult":
        """Submit the job to a scheduler.

        This is the primary programmatic API for job submission.

        Args:
            scheduler: Scheduler to use. If None, auto-detects based on
                       environment (checks HPC_SCHEDULER env var, then
                       probes for SGE_ROOT, sbatch, etc.)

        Returns:
            JobResult with job ID and methods to check status, get output, etc.

        Example:
            job = Job("python train.py", cpu=4, mem="16G")
            result = job.submit()
            print(f"Submitted: {result.job_id}")

            # Wait for completion
            result.wait()
            print(f"Exit code: {result.exit_code}")
        """
        from hpc_runner.schedulers import get_scheduler

        if scheduler is None:
            scheduler = get_scheduler()
        return scheduler.submit(self)

    @classmethod
    def from_config(
        cls,
        tool_or_type: str,
        command: str | None = None,
        **overrides: Any,
    ) -> "Job":
        """Create a job from configuration.

        Looks up job settings from the config file by tool name or job type,
        then applies any overrides.

        Args:
            tool_or_type: Tool name (e.g., "python", "make") or job type
                          (e.g., "interactive", "gpu") from config
            command: Command to run. If None, uses command from config.
            **overrides: Override any job parameters

        Returns:
            Job configured according to config file + overrides

        Example:
            # Config file has [types.gpu] with queue="gpu", resources=[{gpu=1}]
            job = Job.from_config("gpu", command="python train.py")
        """
        from hpc_runner.core.config import get_config

        config = get_config()
        job_config = config.get_job_config(tool_or_type)

        if command is not None:
            job_config["command"] = command
        job_config.update(overrides)

        # Handle resources specially
        if "resources" in job_config and isinstance(job_config["resources"], list):
            resource_set = ResourceSet()
            for r in job_config["resources"]:
                resource_set.add(r["name"], r["value"])
            job_config["resources"] = resource_set

        return cls(**job_config)

    # =========================================================================
    # Attribute Iteration
    # =========================================================================

    def iter_attributes(self) -> Iterator[tuple[str, Any]]:
        """Iterate over renderable attributes that have been set.

        Yields:
            Tuples of (attribute_name, value) for attributes that are not None
            and not equal to their default "skip" values.

        Note:
            The iteration order follows RENDERABLE_ATTRIBUTES, which is
            designed to produce sensible directive ordering.
        """
        for attr_name in self.RENDERABLE_ATTRIBUTES:
            value = getattr(self, attr_name)

            # Skip None values
            if value is None:
                continue

            # Skip False for boolean attributes (they're opt-in)
            # Exception: use_cwd and inherit_env default True, so False means explicit opt-out
            descriptor = getattr(self.__class__, attr_name)
            if isinstance(value, bool) and value is False and descriptor.default is not True:
                continue

            yield attr_name, value

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def merge_output(self) -> bool:
        """Whether to merge stderr into stdout."""
        return self.stderr is None

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _generate_name(self) -> str:
        """Generate a job name from username and command."""
        user = os.environ.get("USER", "user")
        # Extract first meaningful word from command
        cmd_parts = self.command.split()
        for part in cmd_parts:
            if "=" not in part:
                cmd_name = part.split("/")[-1]  # Handle paths
                return f"{user}_{cmd_name}"
        return f"{user}_job"

    def after(
        self,
        *jobs: "JobResult",
        type: str = "afterok",
    ) -> "Job":
        """Add job dependencies.

        Args:
            *jobs: JobResult objects this job depends on
            type: Dependency type (afterok, afterany, afternotok)

        Returns:
            Self for method chaining
        """
        self.dependencies.extend(jobs)
        self.dependency_type = type
        return self

    def __repr__(self) -> str:
        attrs = []
        for attr, value in self.iter_attributes():
            attrs.append(f"{attr}={value!r}")
        return f"Job(command={self.command!r}, {', '.join(attrs)})"
