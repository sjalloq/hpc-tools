HPC Runner
==========

**hpc-runner** provides a unified front end for submitting jobs to HPC
schedulers (SGE, Slurm, PBS) and running them locally for testing.  It
abstracts scheduler-specific flags behind a consistent CLI and Python API,
and uses Environment Modules to ensure reproducible tool environments across
users.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   configuration
   cli
   sge
   programmatic_api
