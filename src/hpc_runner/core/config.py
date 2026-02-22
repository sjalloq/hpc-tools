"""Configuration loading and management."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


# Environment variable for site/system config
HPC_CONFIG_ENV_VAR = "HPC_RUNNER_CONFIG"


@dataclass
class HPCConfig:
    """Loaded configuration."""

    defaults: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
    types: dict[str, dict[str, Any]] = field(default_factory=dict)
    schedulers: dict[str, dict[str, Any]] = field(default_factory=dict)

    _source_paths: list[Path] = field(default_factory=list, repr=False)

    def get_type_config(self, job_type: str) -> dict[str, Any]:
        """Get configuration for a job type.

        Args:
            job_type: Type name to look up in ``[types]``.

        Returns:
            Defaults merged with the matching type entry, or just
            defaults if *job_type* is not found.
        """
        return self._get_job_config(job_type, namespace="types")

    def get_tool_config(self, command: str) -> dict[str, Any]:
        """Get configuration matching a command.

        Extracts tool name from command, looks up base config, then checks
        for option-specific overrides by matching against command arguments.
        """
        parts = command.split()
        tool = Path(parts[0]).name

        # Start with defaults merged with base tool config.
        config = self._get_job_config(tool, namespace="tools")

        # Check for option specialisation.
        tool_section = self.tools.get(tool, {})
        options = tool_section.get("options")
        if options and len(parts) > 1:
            cmd_tokens = _normalise_tokens(parts[1:])
            for option_key, option_config in options.items():
                key_tokens = _normalise_tokens(option_key)
                if _match_contiguous(cmd_tokens, key_tokens):
                    config = _merge(config, option_config)
                    break  # First match wins

        return config

    def _get_job_config(self, name: str, *, namespace: str = "tools") -> dict[str, Any]:
        """Get merged configuration for a tool or type.

        Args:
            name: Tool or type name to look up.
            namespace: Which config section to search — ``"tools"`` (default)
                       or ``"types"``.

        Returns:
            Defaults merged with the matching tool/type entry, or just
            defaults if *name* is not found in the requested namespace.
        """
        config = self.defaults.copy()

        section = self.types if namespace == "types" else self.tools
        if name in section:
            # Shallow copy to avoid mutating the original.
            tool_config = section[name].copy()
            tool_config.pop("options", None)  # Handled separately by get_tool_config
            config = _merge(config, tool_config)

        return config

    def get_scheduler_config(self, scheduler: str) -> dict[str, Any]:
        """Get scheduler-specific configuration."""
        return self.schedulers.get(scheduler, {})


def _normalise_tokens(args: str | list[str]) -> list[str]:
    """Tokenise and normalise command arguments.

    Splits --flag=value into separate tokens. Does not attempt to
    interpret short options or combined flags.
    """
    if isinstance(args, str):
        tokens = args.split()
    else:
        tokens = list(args)

    normalised: list[str] = []
    for token in tokens:
        if token.startswith("--") and "=" in token:
            flag, _, value = token.partition("=")
            normalised.append(flag)
            normalised.append(value)
        else:
            normalised.append(token)
    return normalised


def _match_contiguous(haystack: list[str], needle: list[str]) -> bool:
    """Check if needle tokens appear as a contiguous sequence in haystack."""
    if not needle:
        return False
    needle_len = len(needle)
    for i in range(len(haystack) - needle_len + 1):
        if haystack[i : i + needle_len] == needle:
            return True
    return False


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # Check for list reset marker
            if value and value[0] == "-":
                result[key] = value[1:]
            else:
                seen: set[Any] = set()
                merged: list[Any] = []
                for item in result[key] + value:
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[key] = merged
        else:
            result[key] = value
    return result


def _expand_env_vars(path_str: str) -> str:
    """Expand environment variables in a path string.

    Supports ${VAR} and $VAR syntax.
    """

    # Handle ${VAR} syntax
    def replace_braced(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    result = re.sub(r"\$\{([^}]+)\}", replace_braced, path_str)

    # Handle $VAR syntax (word characters only)
    def replace_simple(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    result = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", replace_simple, result)

    return result


def _resolve_extends(config_path: Path, seen: set[Path] | None = None) -> list[Path]:
    """Resolve extends chain for a config file.

    Returns list of paths in order they should be merged (base first).
    Detects circular dependencies.
    """
    if seen is None:
        seen = set()

    config_path = config_path.resolve()

    if config_path in seen:
        raise ValueError(f"Circular extends detected: {config_path}")

    seen.add(config_path)

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return [config_path]

    extends = data.get("extends")
    if not extends:
        return [config_path]

    # Expand env vars and resolve relative to config file's directory
    extends_expanded = _expand_env_vars(extends)
    extends_path = Path(extends_expanded)

    if not extends_path.is_absolute():
        extends_path = config_path.parent / extends_path

    extends_path = extends_path.resolve()

    if not extends_path.exists():
        # Warning but don't fail - the extends target might not exist yet
        return [config_path]

    # Recursively resolve the parent's extends
    parent_chain = _resolve_extends(extends_path, seen)

    return parent_chain + [config_path]


def find_config_files() -> list[Path]:
    """Find all configuration files to merge.

    Returns list of paths in merge order (first = lowest priority).

    Merge order:
    1. $HPC_RUNNER_CONFIG (if set) - site/system defaults
    2. ~/.config/hpc-runner/{config.toml,hpc-runner.toml} - user defaults
    3. <git-root>/hpc-runner.toml (with extends resolution)
    4. ./hpc-runner.toml or ./pyproject.toml (with extends resolution)
    """
    configs: list[Path] = []
    seen: set[Path] = set()

    def add_config(path: Path) -> None:
        """Add config and its extends chain, avoiding duplicates."""
        resolved = path.resolve()
        if resolved in seen:
            return

        # Resolve extends chain
        chain = _resolve_extends(path)
        for p in chain:
            if p not in seen:
                seen.add(p)
                configs.append(p)

    # 1. Environment variable config (site/system defaults)
    env_config = os.environ.get(HPC_CONFIG_ENV_VAR)
    if env_config:
        env_path = Path(_expand_env_vars(env_config))
        if env_path.exists():
            add_config(env_path)

    # 2. User config (check both config.toml and hpc-runner.toml)
    user_config_dir = Path.home() / ".config" / "hpc-runner"
    for user_config_name in ("config.toml", "hpc-runner.toml"):
        user_config = user_config_dir / user_config_name
        if user_config.exists():
            add_config(user_config)
            break  # Use first one found

    # 3. Git root config
    cwd = Path.cwd()
    git_root = _find_git_root(cwd)
    if git_root:
        git_config = git_root / "hpc-runner.toml"
        if git_config.exists():
            add_config(git_config)

    # 4. Current directory config
    if (cwd / "hpc-runner.toml").exists():
        add_config(cwd / "hpc-runner.toml")
    elif (cwd / "pyproject.toml").exists():
        try:
            with open(cwd / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            if "tool" in pyproject and "hpc-runner" in pyproject["tool"]:
                add_config(cwd / "pyproject.toml")
        except Exception:
            pass

    return configs


def find_config_file() -> Path | None:
    """Find the highest priority configuration file.

    For backwards compatibility. Returns the last (highest priority) config.
    """
    configs = find_config_files()
    return configs[-1] if configs else None


def _find_git_root(start: Path) -> Path | None:
    """Find git repository root."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def _load_single_config(path: Path) -> dict[str, Any]:
    """Load a single config file and return its data dict."""
    with open(path, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    # Handle pyproject.toml
    if path.name == "pyproject.toml":
        tool_section = data.get("tool", {})
        if isinstance(tool_section, dict):
            hpc_section = tool_section.get("hpc-runner", {})
            data = dict(hpc_section) if isinstance(hpc_section, dict) else {}
        else:
            data = {}

    # Remove 'extends' key - it's metadata, not config
    data.pop("extends", None)

    return data


def load_config(path: Path | str | None = None) -> HPCConfig:
    """Load and merge configuration from all discovered files.

    Args:
        path: Explicit config path or None to auto-discover and merge all
    """
    if path is not None:
        # Explicit path - load just that file (with its extends chain)
        path = Path(path)
        config_files = _resolve_extends(path)
    else:
        # Auto-discover and merge all
        config_files = find_config_files()

    if not config_files:
        return HPCConfig()  # Empty config

    # Merge all configs in order (first = lowest priority)
    merged: dict[str, Any] = {
        "defaults": {},
        "tools": {},
        "types": {},
        "schedulers": {},
    }

    for config_path in config_files:
        try:
            data = _load_single_config(config_path)
            for key in merged:
                if key in data:
                    merged[key] = _merge(merged[key], data[key])
        except Exception:
            # Skip files that fail to load
            continue

    config = HPCConfig(
        defaults=merged["defaults"],
        tools=merged["tools"],
        types=merged["types"],
        schedulers=merged["schedulers"],
    )
    config._source_paths = config_files

    return config


# Global config cache
_cached_config: HPCConfig | None = None


def get_config() -> HPCConfig:
    """Get the global configuration (cached)."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config


def reload_config(path: Path | str | None = None) -> HPCConfig:
    """Reload configuration (clears cache)."""
    global _cached_config
    _cached_config = load_config(path)
    return _cached_config
