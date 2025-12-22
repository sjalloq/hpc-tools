"""Main HPC Monitor TUI application.

Uses modern Textual patterns:
- Reactive attributes for automatic UI updates
- Workers with @work decorator for async scheduler calls
- set_interval for auto-refresh
- Message-based event handling
"""

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static


class HpcMonitorApp(App[None]):
    """Textual app for monitoring HPC jobs.

    Attributes:
        refresh_interval: Seconds between auto-refresh of job data.
        user_filter: Filter jobs by "me" (current user) or "all" users.
        auto_refresh_enabled: Whether auto-refresh is active.
    """

    CSS_PATH: ClassVar[Path] = Path(__file__).parent / "styles" / "monitor.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("u", "toggle_user", "Toggle User"),
    ]

    # Reactive attributes - changes automatically trigger watch methods
    user_filter: reactive[str] = reactive("me")
    auto_refresh_enabled: reactive[bool] = reactive(True)

    def __init__(self, refresh_interval: int = 10) -> None:
        """Initialize the HPC Monitor app.

        Args:
            refresh_interval: Seconds between auto-refresh cycles.
        """
        super().__init__()
        self._refresh_interval = refresh_interval

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("HPC Monitor - Coming Soon", id="placeholder")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted - set up timers and initial data fetch."""
        # Set up auto-refresh timer (paused initially until we have real data)
        self._refresh_timer = self.set_interval(
            self._refresh_interval,
            self._on_refresh_timer,
            pause=True,
        )

    def _on_refresh_timer(self) -> None:
        """Called by the refresh timer - triggers data fetch."""
        if self.auto_refresh_enabled:
            self.action_refresh()

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Manually trigger a data refresh."""
        # Will be implemented when we add the job provider
        self.notify("Refreshing...", timeout=1)

    def action_toggle_user(self) -> None:
        """Toggle between showing current user's jobs and all jobs."""
        self.user_filter = "all" if self.user_filter == "me" else "me"

    def watch_user_filter(self, old_value: str, new_value: str) -> None:
        """React to user filter changes."""
        self.notify(f"Filter: {new_value}", timeout=1)
        # Will trigger data refresh when job provider is added
