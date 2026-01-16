CLI
===

The primary entry point is the ``hpc`` command.

.. note::

   This page focuses on the stable “user facing” flags. Any unknown options that
   start with ``-`` are passed through to the underlying scheduler (e.g. SGE
   ``qsub`` flags like ``-q`` and ``-l``).


Global options
--------------

These options come before the subcommand:

- ``--config PATH``: use an explicit config file (bypasses discovery)
- ``--scheduler NAME``: force a scheduler (``sge``, ``slurm``, ``pbs``, ``local``)
- ``--verbose``: extra debug output


``hpc run`` (submit)
--------------------

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
- ``--keep-script`` (debug: keep generated script)

Examples:

.. code-block:: bash

   hpc run --cpu 4 --mem 16G --time 2:00:00 "python train.py"
   hpc run --job-type gpu "python train.py"
   hpc run -q gpu.q -l gpu=1 "python train.py"   # scheduler passthrough


``submit`` alias
----------------

There is also a convenience console script called ``submit`` which behaves like:

.. code-block:: bash

   submit ...  ==  hpc run ...

It still supports global flags:

.. code-block:: bash

   submit --config ./hpc-runner.toml --scheduler sge --dry-run "python train.py"


Other commands
--------------

- ``hpc status JOB_ID``: show job status
- ``hpc cancel JOB_ID``: cancel a job
- ``hpc monitor``: launch the TUI job monitor
- ``hpc config show``: print the active config file contents
- ``hpc config path``: print the active config file path
- ``hpc config init [--global]``: create a starter config

