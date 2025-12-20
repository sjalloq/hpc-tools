"""Tests for configuration system."""

import os
from pathlib import Path

import pytest

from hpc_runner.core.config import HPCConfig, find_config_file, load_config


class TestHPCConfig:
    """Tests for HPCConfig class."""

    def test_empty_config(self):
        """Test empty configuration."""
        config = HPCConfig()
        assert config.defaults == {}
        assert config.tools == {}
        assert config.types == {}

    def test_get_job_config_defaults(self):
        """Test getting job config falls back to defaults."""
        config = HPCConfig(defaults={"cpu": 2, "mem": "8G"})
        job_config = config.get_job_config("unknown_tool")

        assert job_config["cpu"] == 2
        assert job_config["mem"] == "8G"

    def test_get_job_config_tool(self):
        """Test getting job config for a tool."""
        config = HPCConfig(
            defaults={"cpu": 1, "mem": "4G"},
            tools={"python": {"cpu": 4, "modules": ["python/3.11"]}},
        )
        job_config = config.get_job_config("python")

        assert job_config["cpu"] == 4  # Overridden
        assert job_config["mem"] == "4G"  # From defaults
        assert job_config["modules"] == ["python/3.11"]

    def test_get_job_config_type(self):
        """Test getting job config for a type."""
        config = HPCConfig(
            defaults={"cpu": 1},
            types={"gpu": {"queue": "gpu", "resources": [{"name": "gpu", "value": 1}]}},
        )
        job_config = config.get_job_config("gpu")

        assert job_config["cpu"] == 1  # From defaults
        assert job_config["queue"] == "gpu"

    def test_get_tool_config_extracts_name(self):
        """Test that get_tool_config extracts tool name from command."""
        config = HPCConfig(
            tools={"python": {"cpu": 4}},
        )
        job_config = config.get_tool_config("python script.py --arg value")

        assert job_config["cpu"] == 4

    def test_get_scheduler_config(self):
        """Test getting scheduler-specific config."""
        config = HPCConfig(
            schedulers={"sge": {"parallel_environment": "mpi"}},
        )
        sge_config = config.get_scheduler_config("sge")

        assert sge_config["parallel_environment"] == "mpi"

    def test_get_scheduler_config_missing(self):
        """Test getting config for missing scheduler."""
        config = HPCConfig()
        sge_config = config.get_scheduler_config("sge")

        assert sge_config == {}


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_config_from_file(self, sample_config):
        """Test loading config from a file."""
        config = load_config(sample_config)

        assert config.defaults["cpu"] == 2
        assert config.defaults["mem"] == "8G"
        assert config.schedulers["sge"]["parallel_environment"] == "mpi"

    def test_load_config_uses_package_defaults(self, temp_dir):
        """Test that loading uses package defaults when no user config found."""
        # Change to temp dir where there's no user config
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            config = load_config()
            # Package defaults should be loaded
            assert "cpu" in config.defaults
            assert "mem" in config.defaults
        finally:
            os.chdir(old_cwd)


class TestFindConfigFile:
    """Tests for config file discovery."""

    def test_find_config_in_current_dir(self, temp_dir):
        """Test finding config in current directory."""
        config_file = temp_dir / "hpc-tools.toml"
        config_file.write_text("[defaults]\ncpu = 1\n")

        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            found = find_config_file()
            assert found == config_file
        finally:
            os.chdir(old_cwd)

    def test_find_config_in_pyproject(self, temp_dir):
        """Test finding config in pyproject.toml."""
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text('[tool.hpc-tools]\n[tool.hpc-tools.defaults]\ncpu = 1\n')

        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            found = find_config_file()
            assert found == pyproject
        finally:
            os.chdir(old_cwd)
