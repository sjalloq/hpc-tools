"""SGE output parsing utilities."""

import re
from datetime import datetime
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
        _strip_namespaces(root)

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
    """Parse a single job_list element.

    SGE XML elements include:
    - JB_job_number: Job ID
    - JB_name: Job name
    - JB_owner: Username
    - state: Job state (r, qw, hqw, etc.)
    - queue_name: Queue@host (for running jobs)
    - hard_req_queue: Requested queue (for pending jobs)
    - slots: Number of slots/CPUs
    - JB_submission_time: Submission timestamp (epoch)
    - JAT_start_time: Start timestamp (epoch, running jobs only)
    - tasks: Array task ID (for array jobs)
    """
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

    # Owner/user
    owner_elem = elem.find("JB_owner")
    if owner_elem is not None and owner_elem.text:
        job_info["user"] = owner_elem.text

    # State
    state_elem = elem.find("state")
    if state_elem is not None and state_elem.text:
        job_info["state"] = state_elem.text

    # Queue - running jobs have queue_name, pending may have hard_req_queue
    queue_elem = elem.find("queue_name")
    if queue_elem is not None and queue_elem.text:
        # Format is usually "queue@host", extract queue and host separately
        queue_full = queue_elem.text
        if "@" in queue_full:
            queue_name, host = queue_full.split("@", 1)
            job_info["queue"] = queue_name
            job_info["node"] = host
        else:
            job_info["queue"] = queue_full
    else:
        # Check for requested queue (pending jobs)
        hard_queue = elem.find("hard_req_queue")
        if hard_queue is not None and hard_queue.text:
            job_info["queue"] = hard_queue.text

    # Slots (CPU count)
    slots_elem = elem.find("slots")
    if slots_elem is not None and slots_elem.text:
        job_info["slots"] = int(slots_elem.text)

    # Submission time (epoch seconds)
    submit_text = elem.findtext(".//JB_submission_time")
    if submit_text:
        try:
            job_info["submit_time"] = int(submit_text)
        except ValueError:
            pass

    # Start time (epoch seconds, only for running jobs)
    start_text = elem.findtext(".//JAT_start_time")
    if start_text:
        start_epoch = _parse_sge_timestamp(start_text)
        if start_epoch is not None:
            job_info["start_time"] = start_epoch

    # Array task ID
    tasks_elem = elem.find("tasks")
    if tasks_elem is not None and tasks_elem.text:
        job_info["array_task_id"] = tasks_elem.text

    return job_info


def _strip_namespaces(root: ET.Element) -> None:
    """Strip XML namespaces so ElementTree finds simple tag names."""
    for elem in root.iter():
        if isinstance(elem.tag, str) and "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]


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

            # Parse submit/start time (MM/DD/YYYY HH:MM:SS)
            if len(parts) >= 7:
                timestamp = _parse_qstat_datetime(parts[5], parts[6])
                if timestamp is not None:
                    if "r" in parts[4]:
                        jobs[job_id]["start_time"] = timestamp
                    else:
                        jobs[job_id]["submit_time"] = timestamp

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


def _parse_qstat_datetime(date_part: str, time_part: str) -> int | None:
    """Parse qstat date/time into epoch seconds."""
    try:
        dt = datetime.strptime(f"{date_part} {time_part}", "%m/%d/%Y %H:%M:%S")
    except ValueError:
        return None
    return int(dt.timestamp())


def _parse_sge_timestamp(value: str) -> int | None:
    """Parse SGE timestamps that may be epoch seconds or ISO 8601."""
    if value.isdigit():
        try:
            return int(value)
        except ValueError:
            return None
    try:
        return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").timestamp())
    except ValueError:
        return None


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

    # Deleting or error states take precedence over other flags.
    if "d" in state:
        return JobStatus.CANCELLED
    if "e" in state:
        return JobStatus.FAILED

    # Running or transferring states.
    if "r" in state or "t" in state:
        return JobStatus.RUNNING

    # Queued, held, or suspended states.
    if "q" in state or "h" in state or "s" in state:
        return JobStatus.PENDING

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
