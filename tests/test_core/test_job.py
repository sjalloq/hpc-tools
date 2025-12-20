"""Tests for Job model."""

import os

import pytest

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
