"""Jinja2 template engine for job scripts."""

from pathlib import Path
from typing import Any

import jinja2

# Template directories - schedulers and package templates
_SCHEDULERS_DIR = Path(__file__).parent.parent / "schedulers"
_PACKAGE_DIR = Path(__file__).parent

_env: jinja2.Environment | None = None


def _get_env() -> jinja2.Environment:
    """Get or create the Jinja2 environment."""
    global _env
    if _env is None:
        _env = jinja2.Environment(
            loader=jinja2.FileSystemLoader([str(_SCHEDULERS_DIR), str(_PACKAGE_DIR)]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
    return _env


def render_template(name: str, **context: Any) -> str:
    """Render a template.

    Args:
        name: Template name (e.g., "sge/templates/job.sh.j2")
        **context: Template context variables

    Returns:
        Rendered template content
    """
    env = _get_env()
    template = env.get_template(name)
    return template.render(**context)


def render_string(template_str: str, **context: Any) -> str:
    """Render a template string.

    Args:
        template_str: Template content as a string
        **context: Template context variables

    Returns:
        Rendered content
    """
    env = _get_env()
    template = env.from_string(template_str)
    return template.render(**context)
