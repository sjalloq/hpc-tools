"""Filter bar component for job tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Select, Static

from hpc_runner.core.result import JobStatus

if TYPE_CHECKING:
    from textual.app import ComposeResult


# Status options for the dropdown
STATUS_OPTIONS: list[tuple[str, str | None]] = [
    ("All", None),
    ("Running", "running"),
    ("Pending", "pending"),
    ("Held", "held"),
]


class FilterBar(Horizontal):
    """Composable filter bar for job tables.

    Provides status filter, queue filter, and search input.
    Emits FilterChanged messages when any filter value changes.
    """

    @dataclass
    class FilterChanged(Message):
        """Emitted when any filter value changes."""

        status: str | None
        queue: str | None
        search: str

        @property
        def control(self) -> FilterBar:
            """The FilterBar that sent this message."""
            return self._sender  # type: ignore[return-value]

    DEFAULT_CSS = """
    FilterBar {
        height: 3;
        padding: 0 1;
        background: transparent;
    }

    FilterBar > Static.filter-label {
        width: auto;
        padding: 0 1 0 0;
        content-align: center middle;
    }

    FilterBar > Select {
        width: 16;
        margin-right: 2;
    }

    FilterBar > Input {
        width: 24;
    }
    """

    def __init__(
        self,
        queues: list[str] | None = None,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the filter bar.

        Args:
            queues: List of queue names for the queue dropdown.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(id=id, classes=classes)
        self._queues = queues or []
        self._current_status: str | None = None
        self._current_queue: str | None = None
        self._current_search: str = ""

    def compose(self) -> ComposeResult:
        """Create filter bar widgets."""
        yield Static("Status:", classes="filter-label")
        yield Select(
            STATUS_OPTIONS,
            value=None,
            allow_blank=False,
            id="status-filter",
        )

        yield Static("Queue:", classes="filter-label")
        queue_options: list[tuple[str, str | None]] = [("All", None)]
        queue_options.extend((q, q) for q in self._queues)
        yield Select(
            queue_options,
            value=None,
            allow_blank=False,
            id="queue-filter",
        )

        yield Input(placeholder="Search name/ID...", id="search-filter")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle dropdown selection changes."""
        if event.select.id == "status-filter":
            self._current_status = event.value
        elif event.select.id == "queue-filter":
            self._current_queue = event.value

        self._emit_filter_changed()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-filter":
            self._current_search = event.value
            self._emit_filter_changed()

    def _emit_filter_changed(self) -> None:
        """Emit a FilterChanged message with current filter values."""
        self.post_message(
            self.FilterChanged(
                status=self._current_status,
                queue=self._current_queue,
                search=self._current_search,
            )
        )

    def update_queues(self, queues: list[str]) -> None:
        """Update the queue dropdown options.

        Args:
            queues: New list of queue names.
        """
        self._queues = queues
        try:
            queue_select = self.query_one("#queue-filter", Select)
            queue_options: list[tuple[str, str | None]] = [("All", None)]
            queue_options.extend((q, q) for q in queues)
            queue_select.set_options(queue_options)
        except Exception:
            pass  # Widget not yet mounted

    def clear_filters(self) -> None:
        """Reset all filters to default values."""
        try:
            self.query_one("#status-filter", Select).value = None
            self.query_one("#queue-filter", Select).value = None
            self.query_one("#search-filter", Input).value = ""
        except Exception:
            pass

    @property
    def status_filter(self) -> str | None:
        """Current status filter value."""
        return self._current_status

    @property
    def queue_filter(self) -> str | None:
        """Current queue filter value."""
        return self._current_queue

    @property
    def search_filter(self) -> str:
        """Current search filter value."""
        return self._current_search
