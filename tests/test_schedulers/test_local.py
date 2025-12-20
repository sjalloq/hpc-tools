"""Tests for local scheduler."""

import time
from pathlib import Path

import pytest

from hpc_runner.core.job import Job
from hpc_runner.core.result import JobStatus
from hpc_runner.schedulers.local import LocalScheduler


class TestLocalScheduler:
    """Tests for LocalScheduler."""

    def test_scheduler_name(self):
        """Test scheduler name."""
        scheduler = LocalScheduler()
        assert scheduler.name == "local"

    def test_submit_job(self, temp_dir):
        """Test submitting a job."""
        scheduler = LocalScheduler()
        job = Job(command="echo hello", workdir=temp_dir)

        result = scheduler.submit(job)

        assert result.job_id.startswith("local_")
        assert result.scheduler is scheduler
        assert result.job is job

    def test_submit_interactive_job(self, temp_dir):
        """Test submitting an interactive (blocking) job."""
        scheduler = LocalScheduler()
        job = Job(command="echo hello", workdir=temp_dir)

        result = scheduler.submit(job, interactive=True)

        assert result.returncode == 0

    def test_submit_failing_job(self, temp_dir):
        """Test submitting a failing job."""
        scheduler = LocalScheduler()
        job = Job(command="exit 1", workdir=temp_dir)

        result = scheduler.submit(job, interactive=True)

        assert result.returncode == 1

    def test_job_status_running(self, temp_dir):
        """Test getting status of running job."""
        scheduler = LocalScheduler()
        job = Job(command="sleep 10", workdir=temp_dir)

        result = scheduler.submit(job, interactive=False)
        status = scheduler.get_status(result.job_id)

        assert status == JobStatus.RUNNING

        # Clean up
        scheduler.cancel(result.job_id)

    def test_job_status_completed(self, temp_dir):
        """Test getting status of completed job."""
        scheduler = LocalScheduler()
        job = Job(command="echo done", workdir=temp_dir)

        result = scheduler.submit(job, interactive=True)
        status = scheduler.get_status(result.job_id)

        assert status == JobStatus.COMPLETED

    def test_cancel_job(self, temp_dir):
        """Test cancelling a job."""
        scheduler = LocalScheduler()
        job = Job(command="sleep 60", workdir=temp_dir)

        result = scheduler.submit(job, interactive=False)
        success = scheduler.cancel(result.job_id)

        assert success is True

    def test_generate_script(self, temp_dir):
        """Test script generation."""
        scheduler = LocalScheduler()
        job = Job(
            command="echo hello",
            modules=["python/3.11"],
            workdir=temp_dir,
        )

        script = scheduler.generate_script(job)

        assert "#!/bin/bash" in script
        assert "echo hello" in script
        assert "set -e" in script

    def test_output_path(self, temp_dir):
        """Test output file creation."""
        scheduler = LocalScheduler()
        job = Job(command="echo hello", workdir=temp_dir)

        result = scheduler.submit(job, interactive=True)

        stdout_path = scheduler.get_output_path(result.job_id, "stdout")
        assert stdout_path is not None
        assert stdout_path.exists()
        assert "hello" in stdout_path.read_text()

    def test_merged_output(self, temp_dir):
        """Test merged stdout/stderr."""
        scheduler = LocalScheduler()
        job = Job(
            command="echo stdout; echo stderr >&2",
            workdir=temp_dir,
        )

        result = scheduler.submit(job, interactive=True)

        stdout_path = scheduler.get_output_path(result.job_id, "stdout")
        content = stdout_path.read_text()

        assert "stdout" in content
        assert "stderr" in content  # Merged
