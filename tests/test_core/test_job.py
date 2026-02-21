"""Tests for Job model."""

import os
from unittest.mock import patch

from hpc_runner.core.config import HPCConfig
from hpc_runner.core.job import Job
from hpc_runner.core.resources import ResourceSet


class TestJob:
    """Tests for Job class."""

    def test_basic_job_creation(self):
        """Test creating a basic job."""
        job = Job(command="echo hello")
        assert job.command == "echo hello"
        assert job.name is not None  # Auto-generated

    def test_job_with_list_command(self):
        """Test job with command as list."""
        job = Job(command=["python", "script.py", "--arg", "value"])
        assert job.command == "python script.py --arg value"

    def test_job_name_generation(self):
        """Test automatic job name generation."""
        job = Job(command="python script.py")
        user = os.environ.get("USER", "user")
        assert job.name.startswith(f"{user}_")
        assert "python" in job.name

    def test_job_with_explicit_name(self):
        """Test job with explicit name."""
        job = Job(command="echo test", name="my_job")
        assert job.name == "my_job"

    def test_job_with_resources(self):
        """Test job with resources."""
        job = Job(command="echo test", cpu=4, mem="16G", time="2:00:00")
        assert job.cpu == 4
        assert job.mem == "16G"
        assert job.time == "2:00:00"

    def test_job_with_queue(self):
        """Test job with queue."""
        job = Job(command="echo test", queue="gpu")
        assert job.queue == "gpu"

    def test_job_with_modules(self):
        """Test job with modules."""
        job = Job(command="python script.py", modules=["python/3.11", "cuda/12.0"])
        assert job.modules == ["python/3.11", "cuda/12.0"]

    def test_job_merge_output_default(self):
        """Test that merge_output is True by default (stderr=None)."""
        job = Job(command="echo test")
        assert job.merge_output is True
        assert job.stderr is None

    def test_job_separate_stderr(self):
        """Test job with separate stderr."""
        job = Job(command="echo test", stderr="error.log")
        assert job.merge_output is False
        assert job.stderr == "error.log"

    def test_job_with_resource_set(self):
        """Test job with ResourceSet."""
        resources = ResourceSet()
        resources.add("gpu", 2)
        resources.add("license", 1)

        job = Job(command="echo test", resources=resources)
        assert len(job.resources) == 2

    def test_job_with_raw_args(self):
        """Test job with raw scheduler arguments."""
        job = Job(command="echo test", raw_args=["-l", "scratch=10G"])
        assert job.raw_args == ["-l", "scratch=10G"]

    def test_job_with_sge_args(self):
        """Test job with SGE-specific arguments."""
        job = Job(command="echo test", sge_args=["-l", "exclusive=true"])
        assert job.sge_args == ["-l", "exclusive=true"]


class TestJobDependencies:
    """Tests for job dependencies."""

    def test_after_method(self):
        """Test after() method for adding dependencies."""
        from unittest.mock import MagicMock

        # Create mock job results
        result1 = MagicMock()
        result1.job_id = "123"
        result2 = MagicMock()
        result2.job_id = "456"

        job = Job(command="echo test")
        job.after(result1, result2, type="afterok")

        assert len(job.dependencies) == 2
        assert job.dependency_type == "afterok"

    def test_after_returns_self(self):
        """Test that after() returns the job for chaining."""
        from unittest.mock import MagicMock

        result = MagicMock()
        job = Job(command="echo test")
        returned = job.after(result)

        assert returned is job


class TestJobConfigAware:
    """Tests for config-aware Job() construction."""

    def _make_config(
        self,
        defaults: dict | None = None,
        tools: dict | None = None,
        types: dict | None = None,
    ) -> HPCConfig:
        return HPCConfig(
            defaults=defaults or {},
            tools=tools or {},
            types=types or {},
        )

    def test_defaults_applied(self):
        """[defaults] are picked up by Job()."""
        cfg = self._make_config(defaults={"cpu": 2, "mem": "8G", "queue": "batch"})
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo hello")
        assert job.cpu == 2
        assert job.mem == "8G"
        assert job.queue == "batch"

    def test_tool_auto_detected(self):
        """Tool extracted from command is matched to [tools.*]."""
        cfg = self._make_config(
            tools={"python": {"cpu": 4, "modules": ["python/3.11"]}},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="python train.py")
        assert job.cpu == 4
        assert job.modules == ["python/3.11"]

    def test_tool_with_path_stripped(self):
        """/usr/bin/python → python for tool lookup."""
        cfg = self._make_config(
            tools={"python": {"cpu": 8}},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="/usr/bin/python script.py")
        assert job.cpu == 8

    def test_job_type_config_applied(self):
        """job_type= pulls [types.*] config."""
        cfg = self._make_config(
            types={"gpu": {"queue": "gpu.q", "resources": [{"name": "gpu", "value": 1}]}},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="python train.py", job_type="gpu")
        assert job.queue == "gpu.q"
        assert len(job.resources) == 1

    def test_job_type_skips_tool_matching(self):
        """When job_type is given, tool auto-detect is skipped."""
        cfg = self._make_config(
            tools={"python": {"cpu": 99}},
            types={"sim": {"cpu": 2}},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="python run.py", job_type="sim")
        assert job.cpu == 2  # from types.sim, not tools.python

    def test_kwargs_override_config(self):
        """Explicit kwargs beat config values."""
        cfg = self._make_config(
            defaults={"cpu": 2, "mem": "4G"},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo hello", cpu=16, mem="64G")
        assert job.cpu == 16
        assert job.mem == "64G"

    def test_descriptor_defaults_survive(self):
        """No config + no kwargs → descriptor defaults."""
        cfg = self._make_config()
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo hello")
        assert job.inherit_env is True
        assert job.shell == "/bin/bash"
        assert job.use_cwd is True

    def test_config_overrides_descriptor_defaults(self):
        """Config can override shell, inherit_env, use_cwd."""
        cfg = self._make_config(
            defaults={"shell": "/bin/zsh", "inherit_env": False, "use_cwd": False},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo hello")
        assert job.shell == "/bin/zsh"
        assert job.inherit_env is False
        assert job.use_cwd is False

    def test_no_config_files_is_fine(self):
        """Works with completely empty config."""
        cfg = self._make_config()
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo hello")
        assert job.command == "echo hello"
        assert job.name is not None

    def test_config_command_key_ignored(self):
        """A 'command' key in config is stripped — command always comes from caller."""
        cfg = self._make_config(
            defaults={"command": "should be ignored", "cpu": 2},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="echo real")
        assert job.command == "echo real"
        assert job.cpu == 2

    def test_unknown_tool_gets_defaults_only(self):
        """Unrecognised tool falls back to [defaults]."""
        cfg = self._make_config(
            defaults={"cpu": 1},
            tools={"python": {"cpu": 8}},
        )
        with patch("hpc_runner.core.config.get_config", return_value=cfg):
            job = Job(command="unknown_tool arg1")
        assert job.cpu == 1
