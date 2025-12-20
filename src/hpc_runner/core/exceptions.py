"""Custom exceptions for hpc-tools."""


class HPCToolsError(Exception):
    """Base exception for hpc-tools."""


class SchedulerError(HPCToolsError):
    """Error related to scheduler operations."""


class SubmissionError(SchedulerError):
    """Error during job submission."""


class JobNotFoundError(SchedulerError):
    """Job ID not found."""


class ConfigError(HPCToolsError):
    """Error in configuration."""


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""


class ValidationError(HPCToolsError):
    """Validation error for job parameters."""
