"""Auto-detection of available scheduler."""

import os
import shutil


def detect_scheduler() -> str:
    """Auto-detect available scheduler.

    Order of precedence:
    1. HPC_SCHEDULER environment variable
    2. SGE (check for qsub with SGE_ROOT)
    3. Slurm (check for sbatch)
    4. PBS (check for qsub with PBS_CONF_FILE)
    5. Local fallback
    """
    # Environment override
    if scheduler := os.environ.get("HPC_SCHEDULER"):
        return scheduler.lower()

    # Check for SGE (also uses qsub but has SGE_ROOT)
    if shutil.which("qsub") and os.environ.get("SGE_ROOT"):
        return "sge"

    # Check for Slurm
    if shutil.which("sbatch") and shutil.which("squeue"):
        return "slurm"

    # Check for PBS/Torque
    if shutil.which("qsub") and os.environ.get("PBS_CONF_FILE"):
        return "pbs"

    # Fallback to local
    return "local"
