"""Tests for the standalone submit command."""

import os

import pytest
from click.testing import CliRunner

from hpc_runner.cli.submit import submit


class TestSubmitCommand:
    """Tests for the submit command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_help_shows_short_options(self, runner):
        """submit --help should list short-form flags."""
        result = runner.invoke(submit, ["--help"])
        assert result.exit_code == 0
        # rich-click formats as "--type -t" (long first)
        assert "--type" in result.output and "-t" in result.output
        assert "--cpu" in result.output and "-n" in result.output
        assert "--mem" in result.output and "-m" in result.output
        assert "--time" in result.output and "-T" in result.output
        assert "--interactive" in result.output and "-I" in result.output
        assert "--queue" in result.output and "-q" in result.output
        assert "--name" in result.output and "-N" in result.output
        assert "--wait" in result.output and "-w" in result.output
        assert "--array" in result.output and "-a" in result.output
        assert "--env" in result.output and "-e" in result.output
        assert "--depend" in result.output and "-d" in result.output
        assert "--verbose" in result.output and "-v" in result.output
        assert "--dry-run" in result.output

    def test_dry_run_basic(self, runner, temp_dir):
        """submit --dry-run echo hello should produce dry-run output."""
        result = runner.invoke(submit, ["--dry-run", "echo", "hello"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output
        assert "echo hello" in result.output

    def test_dry_run_with_type(self, runner, temp_dir):
        """submit -t <type> --dry-run should use type config."""
        config_file = temp_dir / "hpc-runner.toml"
        config_file.write_text("""
[types.gpu]
queue = "gpu.q"
cpu = 8
""")
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            result = runner.invoke(submit, ["-t", "gpu", "--dry-run", "python", "train.py"])
            assert result.exit_code == 0
            assert "Dry Run" in result.output
            assert "python train.py" in result.output
        finally:
            os.chdir(old_cwd)

    def test_resource_overrides(self, runner, temp_dir):
        """submit -n 4 -m 16G --dry-run should apply resource overrides."""
        result = runner.invoke(submit, ["-n", "4", "-m", "16G", "--dry-run", "python", "script.py"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output
        assert "python script.py" in result.output

    def test_interactive_flag(self, runner, temp_dir):
        """submit -I --dry-run should set interactive mode."""
        result = runner.invoke(submit, ["-I", "--dry-run", "xterm"])
        assert result.exit_code == 0
        assert "interactive" in result.output

    def test_env_vars(self, runner, temp_dir):
        """submit -e FOO=bar should set env vars on the job."""
        result = runner.invoke(
            submit, ["-e", "FOO=bar", "-e", "BAZ=qux", "--dry-run", "echo", "hello"]
        )
        assert result.exit_code == 0
        assert "Dry Run" in result.output

    def test_env_var_bad_format(self, runner):
        """submit -e without = should error."""
        result = runner.invoke(submit, ["-e", "NOEQUALS", "--dry-run", "echo", "hello"])
        assert result.exit_code != 0
        assert "KEY=VAL" in result.output

    def test_unknown_flags_rejected(self, runner):
        """submit should reject unknown flags (closed interface)."""
        result = runner.invoke(submit, ["--nodes", "2", "echo", "hello"])
        assert result.exit_code != 0
        assert "No such option" in result.output or "no such option" in result.output

    def test_requires_command(self, runner):
        """submit with no arguments should error."""
        result = runner.invoke(submit, ["--dry-run"])
        assert result.exit_code != 0

    def test_job_name_option(self, runner, temp_dir):
        """submit -N <name> should set the job name."""
        result = runner.invoke(submit, ["-N", "my_job", "--dry-run", "echo", "hello"])
        assert result.exit_code == 0
        assert "my_job" in result.output

    def test_time_limit_option(self, runner, temp_dir):
        """submit -T 4:00:00 should set time limit."""
        result = runner.invoke(submit, ["-T", "4:00:00", "--dry-run", "echo", "hello"])
        assert result.exit_code == 0
        assert "Dry Run" in result.output

    def test_array_job_dry_run(self, runner, temp_dir):
        """submit -a 1-10 --dry-run should show array job info."""
        result = runner.invoke(submit, ["-a", "1-10", "--dry-run", "echo", "task"])
        assert result.exit_code == 0
        assert "Array job" in result.output
        assert "10 tasks" in result.output

    def test_tool_auto_detection(self, runner, temp_dir):
        """submit should auto-detect tool from command."""
        from hpc_runner.core.config import reload_config

        config_file = temp_dir / "hpc-runner.toml"
        config_file.write_text("""
[tools.python]
cpu = 4
mem = "16G"
modules = ["python/3.11"]
""")
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            reload_config()
            result = runner.invoke(submit, ["--dry-run", "python", "script.py"])
            assert result.exit_code == 0
            assert "python/3.11" in result.output
        finally:
            os.chdir(old_cwd)
