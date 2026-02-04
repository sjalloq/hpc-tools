"""Tests for configuration system."""

import os

from hpc_runner.core.config import HPCConfig, _merge, find_config_file, load_config


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


class TestMerge:
    """Tests for _merge deep merge logic."""

    def test_list_merge_preserves_order(self):
        """Module load order matters on HPC - merge must preserve it."""
        base = {"modules": ["gcc/12", "openmpi/4", "python/3.11"]}
        override = {"modules": ["cuda/12", "python/3.11"]}
        result = _merge(base, override)

        # python/3.11 appears in both - should be deduplicated
        assert result["modules"].count("python/3.11") == 1
        # Order from base should come first, then new items from override
        assert result["modules"] == ["gcc/12", "openmpi/4", "python/3.11", "cuda/12"]

    def test_list_merge_reset_marker(self):
        """The '-' marker should discard the base list entirely."""
        base = {"modules": ["gcc/12", "openmpi/4"]}
        override = {"modules": ["-", "intel/2024", "impi/2024"]}
        result = _merge(base, override)

        assert result["modules"] == ["intel/2024", "impi/2024"]

    def test_list_merge_no_duplicates_from_base(self):
        """Duplicate entries within a single list should be preserved."""
        base = {"args": ["-v"]}
        override = {"args": ["-v", "-x"]}
        result = _merge(base, override)

        # -v appears in both lists but dedup should keep only one
        assert result["args"].count("-v") == 1
        assert "-x" in result["args"]

    def test_dict_merge_deep(self):
        """Nested dicts should merge recursively."""
        base = {"schedulers": {"sge": {"pe": "smp", "mem": "mem_free"}}}
        override = {"schedulers": {"sge": {"pe": "mpi"}}}
        result = _merge(base, override)

        assert result["schedulers"]["sge"]["pe"] == "mpi"
        assert result["schedulers"]["sge"]["mem"] == "mem_free"

    def test_scalar_override(self):
        """Scalars in override should replace base."""
        base = {"cpu": 1, "mem": "4G"}
        override = {"cpu": 8}
        result = _merge(base, override)

        assert result["cpu"] == 8
        assert result["mem"] == "4G"

    def test_new_keys_added(self):
        """Keys only in override should be added."""
        base = {"cpu": 1}
        override = {"queue": "batch"}
        result = _merge(base, override)

        assert result["cpu"] == 1
        assert result["queue"] == "batch"


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
        config_file = temp_dir / "hpc-runner.toml"
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
        pyproject.write_text("[tool.hpc-runner]\n[tool.hpc-runner.defaults]\ncpu = 1\n")

        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            found = find_config_file()
            assert found == pyproject
        finally:
            os.chdir(old_cwd)
