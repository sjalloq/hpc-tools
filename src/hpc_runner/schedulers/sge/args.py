"""SGE-specific argument descriptors."""

from hpc_runner.core.descriptors import SchedulerArg


class SGEArg(SchedulerArg):
    """Base SGE argument.

    SGE uses #$ -flag value format for directives.
    """

    def to_args(self, value) -> list[str]:
        if value is None:
            return []
        return [f"-{self.flag}", str(self.converter(value))]

    def to_directive(self, value) -> str | None:
        if value is None:
            return None
        return f"#$ -{self.flag} {self.converter(value)}"


class SGECpuArg(SGEArg):
    """CPU/slots argument using parallel environment.

    Note: The PE name is configurable via config.
    """

    def __init__(self, pe_name: str = "smp"):
        super().__init__("pe", converter=lambda v: f"{pe_name} {v}", doc="Parallel environment")
        self.pe_name = pe_name

    def to_args(self, value, pe_name: str | None = None) -> list[str]:
        if value is None:
            return []
        pe = pe_name or self.pe_name
        return ["-pe", f"{pe} {value}"]

    def to_directive(self, value, pe_name: str | None = None) -> str | None:
        if value is None:
            return None
        pe = pe_name or self.pe_name
        return f"#$ -pe {pe} {value}"


class SGEMemArg(SGEArg):
    """Memory argument.

    Uses -l resource=value format. Resource name is configurable.
    """

    def __init__(self, resource_name: str = "mem_free"):
        super().__init__("l", doc="Memory requirement")
        self.resource_name = resource_name

    def to_args(self, value, resource_name: str | None = None) -> list[str]:
        if value is None:
            return []
        res = resource_name or self.resource_name
        return ["-l", f"{res}={value}"]

    def to_directive(self, value, resource_name: str | None = None) -> str | None:
        if value is None:
            return None
        res = resource_name or self.resource_name
        return f"#$ -l {res}={value}"


class SGETimeArg(SGEArg):
    """Time limit argument.

    Uses -l h_rt=HH:MM:SS format. Resource name is configurable.
    """

    def __init__(self, resource_name: str = "h_rt"):
        super().__init__("l", doc="Hard runtime limit")
        self.resource_name = resource_name

    def to_args(self, value, resource_name: str | None = None) -> list[str]:
        if value is None:
            return []
        res = resource_name or self.resource_name
        return ["-l", f"{res}={value}"]

    def to_directive(self, value, resource_name: str | None = None) -> str | None:
        if value is None:
            return None
        res = resource_name or self.resource_name
        return f"#$ -l {res}={value}"


class SGEQueueArg(SGEArg):
    """Queue argument."""

    def __init__(self):
        super().__init__("q", doc="Queue name")


class SGEJobNameArg(SGEArg):
    """Job name argument."""

    def __init__(self):
        super().__init__("N", doc="Job name")


class SGEOutputArg(SGEArg):
    """Stdout path argument."""

    def __init__(self):
        super().__init__("o", doc="Stdout file path")


class SGEErrorArg(SGEArg):
    """Stderr path argument."""

    def __init__(self):
        super().__init__("e", doc="Stderr file path")


class SGEArrayArg(SGEArg):
    """Array job argument."""

    def __init__(self):
        super().__init__("t", doc="Array job range (e.g., 1-100, 1-100:10)")


class SGEJoinOutputArg(SGEArg):
    """Join stdout and stderr."""

    def __init__(self):
        super().__init__("j", doc="Join stdout and stderr")

    def to_args(self, value) -> list[str]:
        if value:
            return ["-j", "y"]
        return []

    def to_directive(self, value) -> str | None:
        if value:
            return "#$ -j y"
        return None


class SGECwdArg(SGEArg):
    """Use current working directory."""

    def __init__(self):
        super().__init__("cwd", doc="Use current working directory")

    def to_args(self, value) -> list[str]:
        if value:
            return ["-cwd"]
        return []

    def to_directive(self, value) -> str | None:
        if value:
            return "#$ -cwd"
        return None


class SGEShellArg(SGEArg):
    """Shell to use for the job."""

    def __init__(self):
        super().__init__("S", doc="Shell path")
