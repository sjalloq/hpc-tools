"""Pytest configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_sge_commands():
    """Mock SGE commands (qsub, qstat, etc.)."""
    with patch("subprocess.run") as mock_run:
        def side_effect(cmd, *args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""

            if cmd[0] == "qsub":
                result.stdout = 'Your job 12345 ("test_job") has been submitted\n'
            elif cmd[0] == "qstat":
                if "-j" in cmd:
                    result.stdout = "job_number: 12345\n"
                else:
                    result.stdout = """job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID
-----------------------------------------------------------------------------------------------------------------
12345   0.55500 test_job   user         r     01/01/2024 10:00:00 all.q@node1                    1
"""
            elif cmd[0] == "qdel":
                result.stdout = "user has deleted job 12345\n"
            elif cmd[0] == "qacct":
                result.stdout = """==============================================================
qname        all.q
hostname     node1
owner        user
jobname      test_job
jobnumber    12345
exit_status  0
"""

            return result

        mock_run.side_effect = side_effect
        yield mock_run


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample configuration file."""
    config_content = '''
[defaults]
cpu = 2
mem = "8G"
time = "2:00:00"

[schedulers.sge]
parallel_environment = "mpi"
memory_resource = "h_vmem"

[tools.python]
cpu = 4
modules = ["python/3.11"]

[types.gpu]
queue = "gpu"
resources = [{name = "gpu", value = 1}]
'''
    config_file = temp_dir / "hpc-tools.toml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def clean_env():
    """Clean environment variables that might affect tests."""
    env_vars = ["HPC_SCHEDULER", "SGE_ROOT", "PBS_CONF_FILE"]
    old_values = {var: os.environ.get(var) for var in env_vars}

    for var in env_vars:
        if var in os.environ:
            del os.environ[var]

    yield

    for var, value in old_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]
