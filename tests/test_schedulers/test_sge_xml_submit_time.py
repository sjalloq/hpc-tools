"""Tests for SGE qstat -j -xml parsing."""

from pathlib import Path
import xml.etree.ElementTree as ET

from hpc_runner.schedulers.sge.scheduler import SGEScheduler


def _strip_namespaces(root: ET.Element) -> None:
    """Strip namespaces so ElementTree can match tag names directly."""
    for elem in root.iter():
        if isinstance(elem.tag, str) and "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]


def _find_expected_submit_time(xml_text: str) -> int | None:
    """Extract expected submit time using ElementTree."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    _strip_namespaces(root)
    submit_text = root.findtext(".//JB_submission_time")
    if not submit_text:
        return None
    try:
        return int(submit_text)
    except ValueError:
        return None


def test_qstat_j_xml_submit_time_from_repo_samples() -> None:
    """Parse repo XML samples and ensure submit_time is extracted."""
    scheduler = SGEScheduler()
    xml_files = sorted(Path(".").glob("*.xml"))
    assert xml_files, "No XML files found in repo root for SGE tests."

    missing = []
    for path in xml_files:
        xml_text = path.read_text(errors="ignore")
        expected = _find_expected_submit_time(xml_text)
        if expected is None:
            continue
        parsed = scheduler._parse_qstat_j_xml(xml_text)
        actual = parsed.get("submit_time")
        if actual != expected:
            missing.append((path.name, expected, actual))

    assert not missing, f"Missing or mismatched submit_time: {missing}"
