"""SGE output parsing utilities."""

import re
import xml.etree.ElementTree as ET
from typing import Any

from hpc_runner.core.result import JobStatus


def parse_qstat_xml(xml_output: str) -> dict[str, Any]:
    """Parse qstat -xml output.

    Returns dict with job_id -> job_info mappings.
    """
    jobs: dict[str, Any] = {}

    try:
        root = ET.fromstring(xml_output)

        # Parse queue_info (running jobs)
        for job_list in root.findall(".//job_list"):
            job_info = _parse_job_element(job_list)
            if job_info:
                jobs[job_info["job_id"]] = job_info

        # Parse job_info (pending jobs)
        for job_list in root.findall(".//job_info/job_list"):
            job_info = _parse_job_element(job_list)
            if job_info:
                jobs[job_info["job_id"]] = job_info

    except ET.ParseError:
        pass

    return jobs


def _parse_job_element(elem: ET.Element) -> dict[str, Any] | None:
    """Parse a single job_list element."""
    job_id_elem = elem.find("JB_job_number")
    if job_id_elem is None or job_id_elem.text is None:
        return None

    job_info: dict[str, Any] = {
        "job_id": job_id_elem.text,
    }

    # Job name
    name_elem = elem.find("JB_name")
    if name_elem is not None and name_elem.text:
        job_info["name"] = name_elem.text

    # State
    state_elem = elem.find("state")
    if state_elem is not None and state_elem.text:
        job_info["state"] = state_elem.text

    # Queue
    queue_elem = elem.find("queue_name")
    if queue_elem is not None and queue_elem.text:
        job_info["queue"] = queue_elem.text

    # Slots
    slots_elem = elem.find("slots")
    if slots_elem is not None and slots_elem.text:
        job_info["slots"] = int(slots_elem.text)

    return job_info


def parse_qstat_plain(output: str) -> dict[str, Any]:
    """Parse plain qstat output.

    Format:
    job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID
    --------------------------------------------------------------------------------
    12345   0.55500 myjob      user         r     01/01/2024 10:00:00 all.q@node1                    1
    """
    jobs: dict[str, Any] = {}

    lines = output.strip().split("\n")

    # Skip header lines
    data_started = False
    for line in lines:
        if line.startswith("-"):
            data_started = True
            continue
        if not data_started:
            continue

        parts = line.split()
        if len(parts) >= 5:
            job_id = parts[0]
            jobs[job_id] = {
                "job_id": job_id,
                "priority": parts[1],
                "name": parts[2],
                "user": parts[3],
                "state": parts[4],
            }

            # Parse queue if present
            if len(parts) >= 8:
                jobs[job_id]["queue"] = parts[7]

            # Parse slots if present
            if len(parts) >= 9:
                try:
                    jobs[job_id]["slots"] = int(parts[8])
                except ValueError:
                    pass

    return jobs


def parse_qacct_output(output: str) -> dict[str, Any]:
    """Parse qacct output for job accounting info.

    Format:
    ==============================================================
    qname        all.q
    hostname     node1
    group        users
    owner        user
    jobname      myjob
    jobnumber    12345
    ...
    exit_status  0
    """
    info: dict[str, Any] = {}

    for line in output.strip().split("\n"):
        if line.startswith("="):
            continue

        parts = line.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            info[key] = value.strip()

    return info


def state_to_status(state: str) -> JobStatus:
    """Convert SGE state code to JobStatus.

    SGE states:
    - qw: pending (queued, waiting)
    - hqw: hold (on hold)
    - r: running
    - t: transferring
    - Rr, Rt: restarted
    - s, ts: suspended
    - S, tS: queue suspended
    - T, tT: threshold
    - Eqw: error (waiting)
    - dr: deleting (running)
    - dt: deleting (transferring)
    """
    state = state.lower()

    if state in ("r", "t", "rr", "rt"):
        return JobStatus.RUNNING
    elif state in ("qw", "hqw"):
        return JobStatus.PENDING
    elif state in ("eqw",):
        return JobStatus.FAILED
    elif state in ("dr", "dt"):
        return JobStatus.CANCELLED
    elif state in ("s", "ts", "ss", "ts"):
        return JobStatus.PENDING  # Suspended, treat as pending

    return JobStatus.UNKNOWN


def parse_qsub_output(output: str) -> str | None:
    """Parse qsub output to extract job ID.

    Expected format:
    Your job 12345 ("jobname") has been submitted
    Your job-array 12345.1-10:1 ("jobname") has been submitted
    """
    # Standard job
    match = re.search(r"Your job (\d+)", output)
    if match:
        return match.group(1)

    # Array job
    match = re.search(r"Your job-array (\d+)", output)
    if match:
        return match.group(1)

    return None
