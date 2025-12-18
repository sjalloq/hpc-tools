"""Base descriptor pattern for scheduler arguments."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class SchedulerArg(ABC, Generic[T]):
    """Base descriptor for scheduler arguments.

    Attributes:
        flag: The scheduler's command-line flag name
        converter: Function to convert Python value to string
        validator: Optional validation function
        doc: Documentation string
        env_var: Optional environment variable override
    """

    def __init__(
        self,
        flag: str,
        *,
        converter: Callable[[T], str] = str,
        validator: Callable[[T], bool] | None = None,
        doc: str = "",
        env_var: str | None = None,
    ):
        self.flag = flag
        self.converter = converter
        self.validator = validator
        self.doc = doc
        self.env_var = env_var
        self._name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> T | None:
        if obj is None:
            return self  # type: ignore[return-value]
        return obj.__dict__.get(self._name)  # type: ignore[arg-type]

    def __set__(self, obj: Any, value: T | None) -> None:
        if value is not None and self.validator:
            if not self.validator(value):
                raise ValueError(f"Invalid value for {self._name}: {value}")
        obj.__dict__[self._name] = value  # type: ignore[index]

    @abstractmethod
    def to_args(self, value: T | None) -> list[str]:
        """Convert value to command-line arguments."""

    @abstractmethod
    def to_directive(self, value: T | None) -> str | None:
        """Convert value to script directive (e.g., #SBATCH, #$)."""
