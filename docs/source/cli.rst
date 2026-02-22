CLI
===

The primary entry point is the ``hpc`` command.

There are two entry points:

- ``hpc run`` — full-control interface with scheduler passthrough via ``--``
- ``submit`` — closed, config-driven daily driver with short options


Global options
--------------

These options come before the subcommand:

- ``--config PATH``: use an explicit config file (bypasses discovery)
- ``--scheduler NAME``: force a scheduler (``sge``, ``slurm``, ``pbs``, ``local``)
- ``--verbose``: enable debug-level logging (e.g. shows script paths when
  ``--keep-script`` is used)


``hpc run``
-----------

Submit a job to the scheduler.

Common options:

- ``--job-name TEXT``
- ``--cpu N``
- ``--mem TEXT`` (e.g. ``16G``)
- ``--time TEXT`` (e.g. ``4:00:00``)
- ``--queue TEXT`` (SGE queue)
- ``--directory PATH`` (working dir)
- ``--module TEXT`` (repeatable)
- ``--job-type TEXT`` (named profile from config)
- ``--array TEXT`` (e.g. ``1-100``)
- ``--depend TEXT``
- ``--interactive`` (SGE: qrsh)
- ``--dry-run`` (render, don’t submit)
- ``--wait`` (wait for completion)
- ``--keep-script`` (keep generated script; path is logged at debug level —
  use ``--verbose`` to see it)

Scheduler passthrough
^^^^^^^^^^^^^^^^^^^^^

Use ``--`` to pass raw scheduler arguments. Everything before ``--`` is passed
directly to the scheduler (e.g. ``qsub`` flags); everything after is the
command:

.. code-block:: bash

   # No passthrough — everything is the command
   hpc run python train.py --epochs 10

   # Passthrough — scheduler flags before --, command after
   hpc run -q gpu.q -l gpu=1 -- python train.py
   hpc run --cpu 4 -q batch.q -l scratch=50G -- make -j8 sim

Without ``--``, all arguments are treated as the command. This avoids any
ambiguity between scheduler flags and command flags (e.g. ``mpirun -N 4``
won't be misinterpreted).

Examples:

.. code-block:: bash

   hpc run --cpu 4 --mem 16G --time 2:00:00 python train.py
   hpc run --job-type gpu python train.py
   hpc run -q gpu.q -l gpu=1 -- python train.py
   hpc run --cpu 4 -q batch.q -- mpirun -N 4 ./sim


``submit`` (config-driven daily driver)
----------------------------------------

``submit`` is a closed interface designed for daily use. It exposes the most
common options with short flags and **rejects unknown arguments** — there is
no scheduler passthrough. Instead, scheduler-specific settings should be
defined in the config file under ``[tools.*]`` or ``[types.*]``.

If a tool has ``[tools.<name>.options]`` entries in the config, the command
arguments are matched automatically to apply option-specific overrides (see
:ref:`tool-option-specialisation`).

Short options:

- ``-t TEXT`` — job type from config
- ``-n N`` — number of CPUs
- ``-m TEXT`` — memory (e.g. ``16G``)
- ``-T TEXT`` — time limit
- ``-q TEXT`` — queue/partition
- ``-N TEXT`` — job name
- ``-I`` — interactive
- ``-w`` — wait for completion
- ``-a TEXT`` — array spec
- ``-e TEXT`` — environment variables
- ``-d TEXT`` — dependency
- ``-v`` — verbose

Examples:

.. code-block:: bash

   submit echo hello
   submit -t gpu -n 4 -m 16G python train.py
   submit -n 8 -I xterm
   submit --dry-run make sim


Other commands
--------------

- ``hpc status JOB_ID``: show job status
- ``hpc cancel JOB_ID``: cancel a job
- ``hpc monitor``: launch the TUI job monitor
- ``hpc config show``: print the active config file contents
- ``hpc config path``: print the active config file path
- ``hpc config init [--global]``: create a starter config
