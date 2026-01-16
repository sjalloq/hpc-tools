"""Sphinx documentation configuration for hpc-runner."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# -- Project information -----------------------------------------------------

project = "HPC Runner"
copyright = "2026, Shareef Jalloq"
author = "Shareef Jalloq"

# -- General configuration ---------------------------------------------------

# Make package importable for autodoc (src layout)
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# Avoid autosectionlabel collisions across pages
autosectionlabel_prefix_document = True

# Honor SOURCE_DATE_EPOCH when set (reproducible builds)
if os.environ.get("SOURCE_DATE_EPOCH"):
    today_fmt = "%Y-%m-%d"

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
