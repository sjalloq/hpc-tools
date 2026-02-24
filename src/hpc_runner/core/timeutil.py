"""Time parsing utilities for CLI commands."""

import re
from datetime import datetime, timedelta

_RELATIVE_RE = re.compile(r"^(\d+)([smhd])$")

_UNITS: dict[str, str] = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def parse_since(value: str) -> datetime:
    """Parse a ``--since`` value into a :class:`datetime`.

    Accepted formats:

    * **Relative** – ``"30m"``, ``"2h"``, ``"1d"``, ``"90s"``
      (digits followed by one of ``s/m/h/d``).
    * **Absolute** – any string accepted by :func:`datetime.fromisoformat`,
      e.g. ``"2026-02-23T18:00:00"`` or ``"2026-02-23 18:00"``.

    Returns:
        A :class:`datetime` representing the point in time.

    Raises:
        ValueError: If *value* cannot be parsed as either format.
    """
    match = _RELATIVE_RE.match(value.strip())
    if match:
        amount = int(match.group(1))
        unit = _UNITS[match.group(2)]
        return datetime.now() - timedelta(**{unit: amount})

    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        pass

    raise ValueError(
        f"Invalid --since value: {value!r}. "
        "Use a relative duration (e.g. 30m, 2h, 1d) or an ISO timestamp."
    )
