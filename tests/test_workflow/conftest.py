"""Test fixtures for workflow tests."""

from unittest.mock import patch

import pytest

from hpc_runner.core.config import HPCConfig


@pytest.fixture(autouse=True)
def _isolate_config():
    """Prevent pipeline tests from reading real config files.

    Job() calls get_config() internally.  Patching it here ensures
    pipeline tests are deterministic regardless of the user's local
    configuration files.
    """
    with patch("hpc_runner.core.config.get_config", return_value=HPCConfig()):
        yield
