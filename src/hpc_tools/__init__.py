"""hpc-tools: HPC job submission across multiple schedulers."""

from hpc_tools.core.config import HPCConfig, get_config, load_config, reload_config
from hpc_tools.core.exceptions import (
    ConfigError,
    ConfigNotFoundError,
    HPCToolsError,
    JobNotFoundError,
    SchedulerError,
    SubmissionError,
    ValidationError,
)
from hpc_tools.core.job import Job
from hpc_tools.core.job_array import JobArray
from hpc_tools.core.resources import Resource, ResourceSet
from hpc_tools.core.result import ArrayJobResult, JobResult, JobStatus
from hpc_tools.schedulers import get_scheduler, list_schedulers, register_scheduler
from hpc_tools.workflow import DependencyType, Pipeline, PipelineJob

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "Job",
    "JobArray",
    "JobResult",
    "ArrayJobResult",
    "JobStatus",
    "Resource",
    "ResourceSet",
    # Config
    "load_config",
    "get_config",
    "reload_config",
    "HPCConfig",
    # Schedulers
    "get_scheduler",
    "register_scheduler",
    "list_schedulers",
    # Workflow
    "Pipeline",
    "PipelineJob",
    "DependencyType",
    # Exceptions
    "HPCToolsError",
    "SchedulerError",
    "SubmissionError",
    "JobNotFoundError",
    "ConfigError",
    "ConfigNotFoundError",
    "ValidationError",
]
