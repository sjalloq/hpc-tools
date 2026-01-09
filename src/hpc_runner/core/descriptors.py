"""Descriptor pattern for job attributes and scheduler arguments."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# =============================================================================
# Job Attribute Descriptor
# =============================================================================


class JobAttribute(Generic[T]):
    """Descriptor for Job attributes that enables iteration and rendering.

    This descriptor provides:
    - Clean attribute access on Job instances
    - Class-level access returns the descriptor itself
    - Support for default values
    - Registration for iteration by schedulers

    Example:
        class Job:
            name = JobAttribute('name')
            cpu = JobAttribute('cpu', default=1)

        job = Job()
        job.name = "test"
        print(job.name)  # "test"
        print(Job.name)  # <JobAttribute 'name'>
    """

    def __init__(self, name: str, *, default: T | None = None):
        self.public_name = name
        self.default = default
        self._private_name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._private_name = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> T | "JobAttribute[T]":
        if obj is None:
            return self
        return getattr(obj, self._private_name, self.default)

    def __set__(self, obj: Any, value: T | None) -> None:
        setattr(obj, self._private_name, value)

    def __repr__(self) -> str:
        return f"<JobAttribute '{self.public_name}'>"


# =============================================================================
# Scheduler Argument Base Class
# =============================================================================


class SchedulerArg(ABC, Generic[T]):
    """Base class for scheduler-specific argument renderers.

    Each scheduler backend (SGE, Slurm, PBS) will have subclasses that know
    how to render job attribute values into that scheduler's syntax.

    Subclasses must implement:
    - to_args(value) -> list of command-line arguments
    - to_directive(value) -> script directive string or None

    Example:
        class SGEJobNameArg(SchedulerArg[str]):
            def to_args(self, value):
                return ["-N", value] if value else []

            def to_directive(self, value):
                return f"#$ -N {value}" if value else None
    """

    def __init__(
        self,
        flag: str,
        *,
        doc: str = "",
    ):
        self.flag = flag
        self.doc = doc

    @abstractmethod
    def to_args(self, value: T | None) -> list[str]:
        """Convert value to command-line arguments.

        Args:
            value: The job attribute value (may be None)

        Returns:
            List of command-line argument strings, empty list if value is None
        """

    @abstractmethod
    def to_directive(self, value: T | None) -> str | None:
        """Convert value to a script directive.

        Args:
            value: The job attribute value (may be None)

        Returns:
            Directive string (e.g., "#$ -N jobname") or None if value is None
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} flag='{self.flag}'>"
