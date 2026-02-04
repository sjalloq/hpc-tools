:orphan:

Configuration
=============

This page describes the TOML configuration format used by **hpc-runner** and how
configuration values map to scheduler flags (with a focus on SGE).


Where configuration is loaded from
----------------------------------------

Configuration can be provided via a standalone TOML file or embedded inside
``pyproject.toml``.

Discovery/precedence (highest to lowest):

1. ``./hpc-runner.toml``
2. ``./pyproject.toml`` under ``[tool.hpc-runner]``
3. ``<git root>/hpc-runner.toml``
4. ``~/.config/hpc-runner/config.toml``
5. Package defaults

You can always bypass discovery by providing ``--config /path/to/file.toml``.


Top-level sections
------------------

Configuration supports four top-level namespaces:

- ``[defaults]``: baseline job settings applied to all jobs
- ``[tools.<name>]``: overrides keyed by tool name (e.g., ``python``, ``make``)
- ``[types.<name>]``: named job profiles (e.g., ``gpu``, ``interactive``)
- ``[schedulers.<name>]``: scheduler-specific behavior (e.g., SGE resource names)


How jobs pick up config
-----------------------

When creating a job from config, hpc-runner merges values in this order:

1. start from ``[defaults]``
2. merge either ``[types.<name>]`` **or** ``[tools.<name>]`` (types take precedence)

Then CLI options override whatever came from config.

.. note::

   List values use a "merge by union" strategy.
   If you need to *replace* a list instead of merging, use a leading ``"-"`` entry
   to reset it, e.g. ``modules = ["-", "python/3.11"]``.


SGE mapping notes
-----------------

- ``queue`` maps to SGE ``qsub -q <queue>``.
- ``cpu`` maps to SGE parallel environment slots: ``qsub -pe <parallel_environment> <cpu>``.
- ``mem`` and ``time`` map to SGE hard resources via ``-l <resource>=<value>``, where the
  resource names are configured under ``[schedulers.sge]``.


Example: fully populated config (standalone file)
-------------------------------------------------

Save as ``hpc-runner.toml`` (or ``~/.config/hpc-runner/config.toml``):

.. code-block:: toml

   [defaults]
   scheduler = "auto"          # auto|sge|slurm|pbs|local
   name = "job"
   cpu = 1
   mem = "4G"
   time = "1:00:00"
   queue = "batch.q"           # SGE default queue
   priority = 0
   workdir = "."
   shell = "/bin/bash"
   use_cwd = true
   inherit_env = true

   stdout = "hpc.%N.%J.out"
   stderr = ""                 # empty means "unset"

   modules = ["gcc/12.2", "python/3.11"]
   modules_path = []

   raw_args = []
   sge_args = []

   resources = [
     { name = "scratch", value = "20G" }
   ]

   [schedulers.sge]
   parallel_environment = "smp"
   memory_resource = "mem_free"
   time_resource = "h_rt"

   merge_output = true
   purge_modules = true
   silent_modules = false
   module_init_script = ""
   expand_makeflags = true
   unset_vars = ["https_proxy", "http_proxy"]

   [tools.python]
   cpu = 4
   mem = "16G"
   time = "4:00:00"
   queue = "short.q"
   modules = ["-", "python/3.11"]  # replace list rather than union-merge
   resources = [
     { name = "tmpfs", value = "8G" }
   ]

   [types.interactive]
   queue = "interactive.q"
   time = "8:00:00"
   cpu = 2
   mem = "8G"

   [types.gpu]
   queue = "gpu.q"
   cpu = 8
   mem = "64G"
   time = "12:00:00"
   resources = [
     { name = "gpu", value = 1 }
   ]


Embedding in pyproject.toml
---------------------------

To embed the same config in ``pyproject.toml``, nest the same keys under:

.. code-block:: toml

   [tool.hpc-runner]
   # ... same content as the standalone file ...

