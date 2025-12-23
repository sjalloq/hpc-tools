"""Confirmation modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog.

    Returns True if confirmed, False if cancelled.
    Styles are defined in monitor.tcss.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("s", "screenshot", "Screenshot"),
    ]

    def action_screenshot(self) -> None:
        """Save a screenshot."""
        path = self.app.save_screenshot(path="./")
        self.app.notify(f"Screenshot saved: {path}", timeout=3)

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        confirm_label: str = "Confirm",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._message = message
        self._title = title
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        """Create the modal content."""
        with Vertical(id="confirm-dialog"):
            yield Static(self._message, id="confirm-message", markup=True)
            with Horizontal(id="confirm-buttons"):
                yield Button(self._confirm_label, id="btn-confirm", variant="default")
            yield Static("Esc to dismiss", id="confirm-hint")

    def on_mount(self) -> None:
        """Set up the dialog."""
        dialog = self.query_one("#confirm-dialog", Vertical)
        dialog.border_title = self._title
        # Focus the confirm button
        self.query_one("#btn-confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.dismiss(True)

    def action_confirm(self) -> None:
        """Confirm action (y key)."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel action (n or escape key)."""
        self.dismiss(False)
