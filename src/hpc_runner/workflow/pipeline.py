"""Pipeline API for job workflows with dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hpc_runner.core.job import Job
from hpc_runner.workflow.dependency import DependencyType

if TYPE_CHECKING:
    from hpc_runner.core.result import JobResult
    from hpc_runner.schedulers.base import BaseScheduler


@dataclass
class PipelineJob:
    """A job within a pipeline."""

    job: Job
    name: str
    depends_on: list[PipelineJob] = field(default_factory=list)
    result: JobResult | None = None


class Pipeline:
    """Workflow pipeline with job dependencies.

    Example:
        with Pipeline("build-test") as p:
            build = p.add("make build", name="build", cpu=4)
            test = p.add("make test", name="test", depends_on=["build"])
            package = p.add("make package", name="package", depends_on=["test"])

        results = p.submit()
        p.wait()
    """

    def __init__(self, name: str = "pipeline") -> None:
        self.name = name
        self.jobs: list[PipelineJob] = []
        self._name_map: dict[str, PipelineJob] = {}
        self._submitted = False

    def add(
        self,
        command: str,
        name: str | None = None,
        depends_on: list[str | PipelineJob] | None = None,
        **job_kwargs: Any,
    ) -> PipelineJob:
        """Add a job to the pipeline.

        Args:
            command: Command to execute
            name: Job name (auto-generated if None)
            depends_on: List of job names or PipelineJob objects
            **job_kwargs: Additional Job parameters
        """
        if name is None:
            name = f"step_{len(self.jobs) + 1}"

        if name in self._name_map:
            raise ValueError(f"Job name '{name}' already exists in pipeline")

        job = Job(command=command, name=f"{self.name}_{name}", **job_kwargs)

        dependencies: list[PipelineJob] = []
        if depends_on:
            for dep in depends_on:
                if isinstance(dep, str):
                    if dep not in self._name_map:
                        raise ValueError(f"Unknown dependency: {dep}")
                    dependencies.append(self._name_map[dep])
                else:
                    dependencies.append(dep)

        pipeline_job = PipelineJob(job=job, name=name, depends_on=dependencies)
        self.jobs.append(pipeline_job)
        self._name_map[name] = pipeline_job

        return pipeline_job

    def submit(
        self,
        scheduler: BaseScheduler | None = None,
        dependency_type: DependencyType = DependencyType.AFTEROK,
    ) -> dict[str, JobResult]:
        """Submit all jobs respecting dependencies.

        Args:
            scheduler: Scheduler to use (auto-detect if None)
            dependency_type: Type of dependency to use

        Returns:
            Dict mapping job names to results
        """
        from hpc_runner.schedulers import get_scheduler

        if self._submitted:
            raise RuntimeError("Pipeline has already been submitted")

        if scheduler is None:
            scheduler = get_scheduler()

        results: dict[str, JobResult] = {}

        for pjob in self._topological_sort():
            # Set up dependencies
            if pjob.depends_on:
                dep_results = [results[d.name] for d in pjob.depends_on]
                pjob.job.dependencies = dep_results
                pjob.job.dependency_type = str(dependency_type)

            # Submit
            result = scheduler.submit(pjob.job)
            pjob.result = result
            results[pjob.name] = result

        self._submitted = True
        return results

    def _topological_sort(self) -> list[PipelineJob]:
        """Sort jobs by dependency order (Kahn's algorithm)."""
        # Build in-degree map
        in_degree: dict[str, int] = {pj.name: 0 for pj in self.jobs}
        for pj in self.jobs:
            for dep in pj.depends_on:
                in_degree[pj.name] += 1

        # Find all jobs with no dependencies
        queue = [pj for pj in self.jobs if in_degree[pj.name] == 0]
        result: list[PipelineJob] = []

        while queue:
            pj = queue.pop(0)
            result.append(pj)

            # Reduce in-degree for dependent jobs
            for other_pj in self.jobs:
                if pj in other_pj.depends_on:
                    in_degree[other_pj.name] -= 1
                    if in_degree[other_pj.name] == 0:
                        queue.append(other_pj)

        if len(result) != len(self.jobs):
            raise ValueError("Circular dependency detected in pipeline")

        return result

    def wait(self, poll_interval: float = 5.0) -> dict[str, JobResult]:
        """Wait for all jobs to complete.

        Returns:
            Dict mapping job names to results
        """
        if not self._submitted:
            raise RuntimeError("Pipeline has not been submitted")

        for pjob in self.jobs:
            if pjob.result:
                pjob.result.wait(poll_interval=poll_interval)

        return {pj.name: pj.result for pj in self.jobs if pj.result}

    def get_job(self, name: str) -> PipelineJob | None:
        """Get a job by name."""
        return self._name_map.get(name)

    def __enter__(self) -> Pipeline:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def __len__(self) -> int:
        return len(self.jobs)

    def __iter__(self):
        return iter(self.jobs)
