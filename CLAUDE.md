# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Provides a front end for submitting jobs to an HPC cluster using SGE, Slurm, LSF, etc.  The aim is to enable two things:

1. Abstract away the intricacies of scheduler CLI args and allow the user to submit jobs based on tool name or job type.
2. Use Environment Modules to construct a clean environment for a job and avoid the 'works for me' problem.

### Job/Type Abstraction

Usage model:

```bash
# Launch an extern on the cluster via SGE:
qsub -q <queue> -N <job_name> -cwd -V -l <resources> xterm

# Launch an xterm on the cluster via hpc-runner:
hpc run xterm

# Or launch a script that uses a particular tool using a job type:
hpc run --type xcelium run_sim.sh

# Same thing via submit (short options, config-driven):
submit -t xcelium run_sim.sh
submit -n 4 -m 16G -I xterm
```

Configuration file:

* use a TOML based config file to define defaults for jobs
* define tool flows and specify all scheduler arguments
    * tool flows are detected via the first argument passed to 'hpc run'
* definine job types for flows that don't pass the tool
    * when using makefiles or scripts, the runner can't extract the tool name from the command line

### Consistent Environment

One of the common pitfalls of HPC flows is that what works for one user doesn't always work for another.  Using
Environment Modules means that common tools flows use a fixed tool version for all users.

To accomplish this, the scheduler must purge all modules as part of its setup script and load any modules defined
for the flow.  Each tool or type defined in the configuration file must also define the set of module files that must
be loaded.


## Build & Development Commands

```bash
# Setup virtual environment
source sourceme           # Creates .venv with Python 3.11, installs deps
source sourceme --clean   # Clean rebuild of .venv

# Run tests
pytest                    # All tests
pytest -v                 # Verbose
pytest tests/test_core/   # Specific directory
pytest -k "test_job"      # By name pattern

# Type checking and linting
mypy src/hpc_runner
ruff check src/hpc_runner
ruff format src/hpc_runner

# CLI usage
hpc --help
hpc run --dry-run "echo hello"
hpc --scheduler sge run --cpu 4 --mem 8G "python script.py"

# submit — config-driven shorthand with short options
submit --help
submit --dry-run echo hello
submit -t gpu -n 4 -m 16G python train.py
```

## Architecture

**Package**: `hpc-runner` (PyPI) / `hpc_runner` (import) / `hpc` (CLI)

### Core Abstractions (`src/hpc_runner/core/`)

- **Job** - Central job model with command, resources (cpu/mem/time), modules, dependencies
- **JobResult/ArrayJobResult** - Returned from submission, provides status polling and output access
- **JobStatus** - Unified enum: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, TIMEOUT, UNKNOWN
- **ResourceSet** - Collection of named resources (gpu, licenses, etc.)
- **HPCConfig** - TOML-based config with hierarchy: ./hpc-runner.toml > pyproject.toml > git root > ~/.config > package defaults

### Scheduler System (`src/hpc_runner/schedulers/`)

- **BaseScheduler** - ABC defining submit(), cancel(), get_status(), generate_script()
- **SGEScheduler** - Sun Grid Engine (qsub/qstat/qdel). All SGE-specific settings (PE name, resource names) are configurable via `[schedulers.sge]` config section
- **LocalScheduler** - Runs jobs as local subprocesses (for testing without cluster)
- **detection.py** - Auto-detects scheduler: HPC_SCHEDULER env > SGE_ROOT > sbatch > PBS > local fallback
- **Registry** - `get_scheduler(name)` with lazy imports, `register_scheduler()` for custom schedulers

### CLI (`src/hpc_runner/cli/`)

Uses `rich-click` for styled output. Two entry points:

- **`hpc`** (group) — full-control interface with subcommands: `run`, `status`, `cancel`, `config`, `monitor`
- **`submit`** (standalone) — config-driven daily driver with short options (`-t`, `-n`, `-m`, `-T`, `-I`, `-q`, `-N`, `-w`, `-a`, `-e`, `-d`, `-v`). Closed interface that rejects unknown flags. Builds jobs and submits directly without delegating to `hpc run`.

**`hpc run` vs `submit`**: `hpc run` is the full-control command — it supports scheduler passthrough via `--` separator, long options only, and advanced flags like `--module`, `--nodes`, `--inherit-env`, `--keep-script`, etc. `submit` exposes only the common options with short flags and errors on anything it doesn't recognise. Both construct a `Job()` directly (which auto-consults the TOML config hierarchy) and share the same `_show_dry_run` / `_handle_array_job` helpers (inlined in each module to avoid a circular import through `main.py`).

**Scheduler passthrough on `hpc run`**: Use `--` to pass raw scheduler arguments. Everything before `--` is scheduler passthrough (set on `job.raw_args`), everything after is the command. Without `--`, all args are the command (no heuristic).
```bash
hpc run echo hello                              # no passthrough
hpc run -q batch.q -l gpu=2 -- python train.py  # passthrough
hpc run --cpu 4 -q batch.q -- mpirun -N 4 ./sim # mixed
```

### Workflow (`src/hpc_runner/workflow/`)

**Pipeline** - Job dependency graphs with topological sorting. Jobs reference other jobs by name; dependencies are resolved at submit time.

### Templates (`src/hpc_runner/templates/`)

Jinja2 templates for job scripts. Each scheduler has its own template in `schedulers/{name}/templates/job.sh.j2`.

### TUI (`src/hpc_runner/tui/`)

**HpcMonitorApp** - Textual-based terminal UI for monitoring HPC jobs. Entry point: `hpc monitor`.

- **app.py** - Main application with custom Nord-inspired theme
- **styles/monitor.tcss** - CSS styling following Rovr aesthetic (see `docs/TEXTUAL_STYLING_COOKBOOK.md`)
- **snapshot.py** - Visual review utility for development

## Key Design Decisions

- **Merged output by default**: stderr goes to stdout unless `--stderr` specified
- **Configurable SGE settings**: PE name, memory resource name, time resource name all come from config, not hardcoded
- **Descriptor pattern**: Scheduler arguments use Python descriptors for type-safe flag/directive generation

## TUI Development Rules

### Styling Requirements (CRITICAL)

All TUI components MUST follow these styling patterns. **Do NOT use DEFAULT_CSS in components** - put all styles in `monitor.tcss` for consistency.

**Core Principles:**
- **Transparent backgrounds everywhere** - use `background: transparent` on all widgets
- **Rounded borders** - use `border: round $border-blurred` (unfocused) or `border: round $border` (focused)
- **No solid colored backgrounds** except for highlighted/selected items
- **Border titles in $primary** - use `border-title-color: $primary`

**Standard Widget Patterns:**
```css
/* Panels and containers */
MyWidget {
    background: transparent;
    border: round $border-blurred;
    border-title-color: $primary;
    border-title-background: transparent;
}

MyWidget:focus, MyWidget:focus-within {
    border: round $border;
}

/* Buttons - transparent with border */
Button {
    background: transparent;
    border: round $border-blurred;
    color: $foreground;
}

Button:hover {
    background: $boost;
    border: round $border;
}

/* Popups/overlays - transparent background */
Popup {
    layer: overlay;
    background: transparent;
    border: round $primary;
}
```

**CSS Variables (defined in monitor.tcss):**
- `$border-blurred` - muted border for unfocused elements
- `$border` - bright border for focused elements
- `$primary` - teal accent color (#88C0D0)
- `$error` - red for destructive actions

**Verification:**

After ANY edit to TUI code, verify visually that:
1. All backgrounds are transparent (terminal shows through)
2. Borders are rounded (╭╮╰╯ characters)
3. No solid color blocks except for selected/highlighted items
4. Focus states brighten borders appropriately
