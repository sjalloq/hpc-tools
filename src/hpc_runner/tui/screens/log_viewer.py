"""Log viewer modal screen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea


# Maximum lines to read from large files
MAX_LINES = 5000


class LogViewerScreen(ModalScreen[None]):
    """Modal screen for viewing job log files.

    Displays file content in a scrollable text area.
    Styles are defined in monitor.tcss.
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("g", "go_top", "Top", show=False),
        Binding("G", "go_bottom", "Bottom", show=False),
        Binding("s", "screenshot", "Screenshot", show=False),
    ]

    def __init__(
        self,
        file_path: Path | str,
        title: str = "Log Viewer",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self._title = title
        self._content: str = ""
        self._error: str | None = None

    def compose(self) -> ComposeResult:
        """Create the modal content."""
        with Vertical(id="log-viewer-dialog"):
            yield Static(str(self._file_path), id="log-viewer-path")
            yield TextArea(id="log-viewer-content", read_only=True)
            yield Static("q/Esc close | g top | G bottom", id="log-viewer-hint")

    def on_mount(self) -> None:
        """Set up the dialog and load file content."""
        dialog = self.query_one("#log-viewer-dialog", Vertical)
        dialog.border_title = self._title

        # Load file content
        self._load_file()

        # Update text area with content
        text_area = self.query_one("#log-viewer-content", TextArea)
        if self._error:
            text_area.load_text(self._error)
        else:
            text_area.load_text(self._content)
            # Scroll to bottom by default (most recent output)
            text_area.action_cursor_line_end()
            self.call_after_refresh(self._scroll_to_bottom)

        text_area.focus()

    def _scroll_to_bottom(self) -> None:
        """Scroll text area to bottom."""
        text_area = self.query_one("#log-viewer-content", TextArea)
        # Move cursor to end of document
        text_area.cursor_location = (len(text_area.document.lines) - 1, 0)

    def _load_file(self) -> None:
        """Load content from the log file."""
        if not self._file_path.exists():
            self._error = f"File not found:\n{self._file_path}"
            return

        try:
            # Check file size first
            file_size = self._file_path.stat().st_size

            if file_size == 0:
                self._content = "(empty file)"
                return

            # For large files, read only the last N lines
            if file_size > 1_000_000:  # 1MB threshold
                self._content = self._read_tail()
            else:
                self._content = self._file_path.read_text(encoding="utf-8", errors="replace")

                # Truncate if too many lines
                lines = self._content.splitlines()
                if len(lines) > MAX_LINES:
                    self._content = (
                        f"[Showing last {MAX_LINES} of {len(lines)} lines]\n\n"
                        + "\n".join(lines[-MAX_LINES:])
                    )

        except PermissionError:
            self._error = f"Permission denied:\n{self._file_path}"
        except Exception as e:
            self._error = f"Error reading file:\n{e}"

    def _read_tail(self) -> str:
        """Read the last N lines of a large file efficiently."""
        lines: list[str] = []
        try:
            with open(self._file_path, "rb") as f:
                # Seek to end
                f.seek(0, 2)
                file_size = f.tell()

                # Read chunks from end
                chunk_size = 8192
                position = file_size
                remaining = b""

                while position > 0 and len(lines) < MAX_LINES:
                    read_size = min(chunk_size, position)
                    position -= read_size
                    f.seek(position)
                    chunk = f.read(read_size) + remaining

                    # Split into lines
                    chunk_lines = chunk.split(b"\n")
                    remaining = chunk_lines[0]
                    lines = [
                        line.decode("utf-8", errors="replace")
                        for line in chunk_lines[1:]
                    ] + lines

                # Add any remaining content
                if remaining and len(lines) < MAX_LINES:
                    lines.insert(0, remaining.decode("utf-8", errors="replace"))

            # Trim to MAX_LINES
            if len(lines) > MAX_LINES:
                lines = lines[-MAX_LINES:]

            return f"[Large file - showing last {len(lines)} lines]\n\n" + "\n".join(lines)

        except Exception as e:
            return f"Error reading file: {e}"

    def action_close(self) -> None:
        """Close the log viewer."""
        self.dismiss(None)

    def action_go_top(self) -> None:
        """Scroll to top of file."""
        text_area = self.query_one("#log-viewer-content", TextArea)
        text_area.cursor_location = (0, 0)

    def action_go_bottom(self) -> None:
        """Scroll to bottom of file."""
        text_area = self.query_one("#log-viewer-content", TextArea)
        text_area.cursor_location = (len(text_area.document.lines) - 1, 0)

    def action_screenshot(self) -> None:
        """Save a screenshot."""
        path = self.app.save_screenshot(path="./")
        self.app.notify(f"Screenshot saved: {path}", timeout=3)
