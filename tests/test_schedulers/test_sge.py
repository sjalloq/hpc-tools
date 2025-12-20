"""Tests for SGE scheduler."""

from unittest.mock import MagicMock, patch

import pytest

from hpc_runner.core.job import Job
from hpc_runner.core.result import JobStatus
from hpc_runner.schedulers.sge import SGEScheduler
from hpc_runner.schedulers.sge.parser import (
    parse_qacct_output,
    parse_qstat_plain,
    parse_qsub_output,
    state_to_status,
)


class TestSGEParser:
    """Tests for SGE output parsers."""

    def test_parse_qsub_output(self):
        """Test parsing qsub output."""
        output = 'Your job 12345 ("test_job") has been submitted\n'
        job_id = parse_qsub_output(output)
        assert job_id == "12345"

    def test_parse_qsub_array_output(self):
        """Test parsing qsub array job output."""
        output = 'Your job-array 12345.1-10:1 ("test_job") has been submitted\n'
        job_id = parse_qsub_output(output)
        assert job_id == "12345"

    def test_parse_qstat_plain(self):
        """Test parsing plain qstat output."""
        output = """job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID
-----------------------------------------------------------------------------------------------------------------
12345   0.55500 test_job   user         r     01/01/2024 10:00:00 all.q@node1                    1
12346   0.50000 other_job  user         qw    01/01/2024 09:00:00                                2
"""
        jobs = parse_qstat_plain(output)

        assert "12345" in jobs
        assert jobs["12345"]["state"] == "r"
        assert "12346" in jobs
        assert jobs["12346"]["state"] == "qw"

    def test_parse_qacct_output(self):
        """Test parsing qacct output."""
        output = """==============================================================
qname        all.q
hostname     node1
owner        user
jobname      test_job
jobnumber    12345
exit_status  0
"""
        info = parse_qacct_output(output)

        assert info["qname"] == "all.q"
        assert info["exit_status"] == "0"
        assert info["jobnumber"] == "12345"

    def test_state_to_status(self):
        """Test SGE state to JobStatus mapping."""
        assert state_to_status("r") == JobStatus.RUNNING
        assert state_to_status("qw") == JobStatus.PENDING
        assert state_to_status("Eqw") == JobStatus.FAILED
        assert state_to_status("dr") == JobStatus.CANCELLED


class TestSGEScheduler:
    """Tests for SGEScheduler."""

    def test_scheduler_name(self):
        """Test scheduler name."""
        scheduler = SGEScheduler()
        assert scheduler.name == "sge"

    def test_generate_script(self):
        """Test script generation."""
        scheduler = SGEScheduler()
        job = Job(
            command="echo hello",
            name="test_job",
            cpu=4,
            mem="16G",
            time="2:00:00",
            queue="batch",
        )

        script = scheduler.generate_script(job)

        assert "#!/bin/bash" in script
        assert "#$ -N test_job" in script
        assert "#$ -pe" in script
        assert "echo hello" in script

    def test_generate_script_merged_output(self):
        """Test script generation with merged output."""
        scheduler = SGEScheduler()
        job = Job(command="echo hello", name="test_job")

        script = scheduler.generate_script(job)

        assert "#$ -j y" in script  # Join stdout/stderr

    def test_generate_script_separate_stderr(self):
        """Test script generation with separate stderr."""
        scheduler = SGEScheduler()
        job = Job(command="echo hello", name="test_job", stderr="error.log")

        script = scheduler.generate_script(job)

        assert "#$ -j y" not in script
        assert "#$ -e error.log" in script

    def test_submit_job(self, mock_sge_commands):
        """Test job submission with mocked qsub."""
        scheduler = SGEScheduler()
        job = Job(command="echo hello", name="test_job")

        result = scheduler.submit(job)

        assert result.job_id == "12345"

    def test_cancel_job(self, mock_sge_commands):
        """Test job cancellation."""
        scheduler = SGEScheduler()
        success = scheduler.cancel("12345")
        assert success is True

    def test_get_status(self, mock_sge_commands):
        """Test getting job status."""
        scheduler = SGEScheduler()
        status = scheduler.get_status("12345")
        assert status == JobStatus.RUNNING

    def test_build_submit_command(self):
        """Test building qsub command."""
        scheduler = SGEScheduler()
        job = Job(
            command="echo hello",
            name="test_job",
            cpu=4,
            mem="16G",
            queue="batch",
        )

        cmd = scheduler.build_submit_command(job)

        assert cmd[0] == "qsub"
        assert "-N" in cmd
        assert "test_job" in cmd
        assert "-pe" in cmd
        assert "-q" in cmd

    def test_configurable_pe_name(self):
        """Test that PE name is configurable."""
        with patch("hpc_runner.schedulers.sge.scheduler.get_config") as mock_config:
            mock_config.return_value.get_scheduler_config.return_value = {
                "parallel_environment": "mpi",
                "memory_resource": "h_vmem",
            }

            scheduler = SGEScheduler()
            assert scheduler.pe_name == "mpi"
            assert scheduler.mem_resource == "h_vmem"
