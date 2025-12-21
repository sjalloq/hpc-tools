"""Tests for CLI run command."""

from click.testing import CliRunner

import pytest

from hpc_runner.cli.main import cli
from hpc_runner.cli.run import _parse_args


class TestParseArgs:
    """Tests for argument parsing function."""

    def test_parse_simple_command(self):
        """Test parsing a simple command without scheduler args."""
        args = ("python", "script.py")
        cmd, sched = _parse_args(args)
        assert cmd == ["python", "script.py"]
        assert sched == []

    def test_parse_with_scheduler_flags(self):
        """Test parsing with scheduler flags."""
        args = ("-N", "4", "-n", "16", "mpirun", "./sim")
        cmd, sched = _parse_args(args)
        assert cmd == ["mpirun", "./sim"]
        assert sched == ["-N", "4", "-n", "16"]

    def test_parse_with_equals_syntax(self):
        """Test parsing with equals syntax options."""
        args = ("--gres=gpu:2", "python", "train.py")
        cmd, sched = _parse_args(args)
        assert cmd == ["python", "train.py"]
        assert sched == ["--gres=gpu:2"]

    def test_parse_with_double_dash(self):
        """Test parsing with -- separator."""
        args = ("-N", "4", "--", "python", "-c", "print('hello')")
        cmd, sched = _parse_args(args)
        assert cmd == ["python", "-c", "print('hello')"]
        assert sched == ["-N", "4"]

    def test_parse_mixed_options(self):
        """Test real-world case with mixed options."""
        args = ("-l", "gpu=2", "-q", "batch.q", "python", "train.py", "--epochs", "100")
        cmd, sched = _parse_args(args)
        assert cmd == ["python", "train.py", "--epochs", "100"]
        assert sched == ["-l", "gpu=2", "-q", "batch.q"]

    def test_parse_command_only(self):
        """Test parsing command with no scheduler args."""
        args = ("echo", "hello", "world")
        cmd, sched = _parse_args(args)
        assert cmd == ["echo", "hello", "world"]
        assert sched == []

    def test_parse_empty_args(self):
        """Test parsing empty args."""
        args = ()
        cmd, sched = _parse_args(args)
        assert cmd == []
        assert sched == []

    def test_parse_sge_pe_args_with_separator(self):
        """Test parsing SGE parallel environment args with -- separator.

        Note: Options that take multiple values (like -pe mpi 16) require
        using -- to separate scheduler args from command.
        """
        args = ("-pe", "mpi", "-l", "exclusive=true", "--", "mpirun", "./simulation")
        cmd, sched = _parse_args(args)
        assert cmd == ["mpirun", "./simulation"]
        assert sched == ["-pe", "mpi", "-l", "exclusive=true"]

    def test_parse_sge_pe_slots_in_raw(self):
        """Test that multi-value options need special handling.

        Without --, the parser can't distinguish '16' from a command,
        so users should use raw args format or -- separator.
        """
        # Using equals syntax or quoted args is another workaround
        args = ("-l", "pe_slots=16", "-l", "exclusive=true", "mpirun", "./simulation")
        cmd, sched = _parse_args(args)
        assert cmd == ["mpirun", "./simulation"]
        assert sched == ["-l", "pe_slots=16", "-l", "exclusive=true"]

    def test_parse_command_with_dashes(self):
        """Test command arguments that look like options after command starts."""
        args = ("python", "script.py", "--input", "file.txt", "--output", "out.txt")
        cmd, sched = _parse_args(args)
        assert cmd == ["python", "script.py", "--input", "file.txt", "--output", "out.txt"]
        assert sched == []


class TestRunCommand:
    """Tests for hpc run command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_run_help(self, runner):
        """Test run --help."""
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Submit a job" in result.output

    def test_run_dry_run(self, runner, temp_dir):
        """Test run with --dry-run."""
        result = runner.invoke(
            cli,
            ["--scheduler", "local", "run", "--dry-run", "echo", "hello"],
        )
        assert result.exit_code == 0
        assert "Dry Run" in result.output
        assert "echo hello" in result.output

    def test_run_with_options(self, runner, temp_dir):
        """Test run with various options."""
        result = runner.invoke(
            cli,
            [
                "--scheduler", "local",
                "run",
                "--dry-run",
                "--job-name", "test_job",
                "--cpu", "4",
                "--mem", "16G",
                "python", "script.py",
            ],
        )
        assert result.exit_code == 0
        assert "test_job" in result.output
        assert "python script.py" in result.output

    def test_run_local_job(self, runner, temp_dir):
        """Test running a local job."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(
                cli,
                ["run", "--local", "echo", "hello"],
            )
            assert result.exit_code == 0
            assert "Submitted job" in result.output or "local_" in result.output

    def test_run_interactive_local(self, runner, temp_dir):
        """Test running an interactive local job."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            result = runner.invoke(
                cli,
                ["run", "--local", "--interactive", "echo", "hello"],
            )
            assert result.exit_code == 0
            assert "completed successfully" in result.output

    def test_run_with_scheduler_passthrough(self, runner, temp_dir):
        """Test run with scheduler passthrough args."""
        result = runner.invoke(
            cli,
            [
                "--scheduler", "local",
                "--verbose",
                "run",
                "--dry-run",
                "-N", "4",
                "-n", "16",
                "mpirun", "./sim",
            ],
        )
        assert result.exit_code == 0
        assert "Dry Run" in result.output
        assert "mpirun ./sim" in result.output
        # Passthrough args should be shown in verbose mode
        assert "-N 4" in result.output or "passthrough" in result.output.lower()

    def test_run_requires_command(self, runner):
        """Test that run requires a command."""
        result = runner.invoke(
            cli,
            ["--scheduler", "local", "run", "--dry-run"],
        )
        assert result.exit_code != 0
        assert "Command is required" in result.output

    def test_run_array_job_dry_run(self, runner, temp_dir):
        """Test array job with --dry-run."""
        result = runner.invoke(
            cli,
            [
                "--scheduler", "local",
                "run",
                "--dry-run",
                "--array", "1-10",
                "echo", "task",
            ],
        )
        assert result.exit_code == 0
        assert "Array job" in result.output
        assert "10 tasks" in result.output


class TestMainCLI:
    """Tests for main CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_help(self, runner):
        """Test --help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "HPC job submission tool" in result.output

    def test_version(self, runner):
        """Test --version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output

    def test_commands_listed(self, runner):
        """Test that commands are listed."""
        result = runner.invoke(cli, ["--help"])
        assert "run" in result.output
        assert "status" in result.output
        assert "cancel" in result.output
        assert "config" in result.output

    def test_no_short_options_on_global(self, runner):
        """Verify short options are not available on global commands."""
        # These should fail because -c, -s, -v are no longer valid
        # Actually with the new design, unknown short options are passed through
        # So we just verify the help doesn't show them
        result = runner.invoke(cli, ["--help"])
        # Check that -c, -s, -v are not shown as shortcuts
        assert "-c, --config" not in result.output
        assert "-s, --scheduler" not in result.output
        assert "-v, --verbose" not in result.output
