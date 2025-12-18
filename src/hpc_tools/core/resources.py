"""Resource abstraction for job resource requests."""

from dataclasses import dataclass, field


@dataclass
class Resource:
    """A scheduler resource request.

    Examples:
        Resource("gpu", 2)              # 2 GPUs
        Resource("xilinx", 1)           # 1 Xilinx license
        Resource("mem", "16G")          # Memory
    """

    name: str
    value: int | str

    # Scheduler-specific mappings (populated by scheduler)
    _sge_resource: str | None = field(default=None, repr=False)
    _slurm_gres: str | None = field(default=None, repr=False)


@dataclass
class ResourceSet:
    """Collection of resources for a job."""

    resources: list[Resource] = field(default_factory=list)

    def add(self, name: str, value: int | str) -> "ResourceSet":
        """Add a resource to the set."""
        self.resources.append(Resource(name, value))
        return self

    def get(self, name: str) -> Resource | None:
        """Get a resource by name."""
        for r in self.resources:
            if r.name == name:
                return r
        return None

    def __iter__(self):
        return iter(self.resources)

    def __len__(self) -> int:
        return len(self.resources)

    def __bool__(self) -> bool:
        return bool(self.resources)
