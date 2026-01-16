:orphan:

Programmatic API
================

This page documents the Python API for creating, submitting, and monitoring jobs
from code (without using the CLI).


Installation
------------

.. code-block:: bash

   pip install hpc-runner


Quick start
-----------

.. code-block:: python

   from hpc_runner import Job

   job = Job(command="python my_script.py", cpu=4, mem="8G", time="1:00:00")
   result = job.submit()          # auto-detect scheduler
   final = result.wait()          # block until complete
   print(final, result.returncode)


Creating jobs
-------------

``Job`` is the core unit of work. It’s a scheduler-agnostic data container; a
scheduler implementation is responsible for translating fields into submission
flags/directives.

.. code-block:: python

   from hpc_runner import Job

   job = Job(
       command="python train.py",
       name="training_job",
       cpu=4,
       mem="16G",
       time="4:00:00",
       queue="gpu.q",
       modules=["python/3.11", "cuda/12.0"],
       workdir="/path/to/project",
       stdout="train.out",
       stderr=None,   # None means “merge stderr into stdout” for most schedulers
   )


Submitting jobs
---------------

Submit to an auto-detected scheduler:

.. code-block:: python

   result = job.submit()

Or explicitly select a scheduler:

.. code-block:: python

   from hpc_runner import get_scheduler

   scheduler = get_scheduler("sge")
   result = scheduler.submit(job)


Monitoring jobs
---------------

``Job.submit()`` returns a ``JobResult`` which can be polled or waited on.

.. code-block:: python

   from hpc_runner import Job, JobStatus

   result = Job("python train.py").submit()

   while not result.is_complete:
       print(result.job_id, result.status)

   if result.status == JobStatus.COMPLETED:
       print("ok:", result.read_stdout(tail=20))
   else:
       print("failed:", result.read_stderr(tail=50))

Cancel a job:

.. code-block:: python

   result.cancel()


Configuration-driven jobs
-------------------------

``Job.from_config()`` merges your config ``[defaults]`` with a named ``[types.<name>]``
or ``[tools.<name>]`` section, then applies overrides you pass in code.

.. code-block:: python

   from hpc_runner import Job, reload_config

   # Explicitly load a config file for this process (optional)
   reload_config("./hpc-runner.toml")

   job = Job.from_config("gpu", command="python train.py", cpu=8)
   result = job.submit()


Job dependencies
----------------

At the low level, you can chain jobs by attaching a dependency to a new job:

.. code-block:: python

   from hpc_runner import Job

   r1 = Job("python preprocess.py", name="pre").submit()
   j2 = Job("python train.py", name="train")
   j2.dependencies = [r1]     # programmatic dependency
   j2.dependency_type = "afterok"
   r2 = j2.submit()


Pipelines (multi-step workflows)
--------------------------------

For larger workflows, use ``Pipeline`` to define steps and dependencies by name.

.. code-block:: python

   from hpc_runner import Pipeline

   with Pipeline("ml") as p:
       p.add("python preprocess.py", name="preprocess", cpu=8, mem="32G")
       p.add("python train.py", name="train", depends_on=["preprocess"], queue="gpu.q")
       p.add("python evaluate.py", name="evaluate", depends_on=["train"])

   results = p.submit()
   p.wait()

   for step, res in results.items():
       print(step, res.status, res.returncode)


Array jobs
----------

Use ``JobArray`` when you want a scheduler array job (SGE: ``qsub -t``):

.. code-block:: python

   from hpc_runner import Job, JobArray

   base = Job("python work.py", name="work", cpu=2, time="0:30:00")
   array = JobArray(job=base, start=1, end=100, max_concurrent=10)
   array_result = array.submit()

   statuses = array_result.wait()
   print("completed:", sum(1 for s in statuses.values() if s.name == "COMPLETED"))

