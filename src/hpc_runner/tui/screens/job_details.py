"""Job details modal screen."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea

if TYPE_CHECKING:
    from hpc_runner.core.job_info import JobInfo


class JobDetailsScreen(ModalScreen[None]):
    """Modal screen for viewing full job details.

    Displays comprehensive job information including all resource requests,
    paths, dependencies, and other metadata.
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
        job: JobInfo,
        extra_details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the job details screen.

        Args:
            job: The JobInfo object to display.
            extra_details: Additional details from qstat -j (resources, etc.)
        """
        super().__init__(**kwargs)
        self._job = job
        self._extra = extra_details or {}

    def compose(self) -> ComposeResult:
        """Create the modal content."""
        with Vertical(id="job-details-dialog"):
            yield TextArea(id="job-details-content", read_only=True)
            yield Static("q/Esc close | g top | G bottom", id="job-details-hint")

    def on_mount(self) -> None:
        """Set up the dialog with job content."""
        dialog = self.query_one("#job-details-dialog", Vertical)
        # Keep title short to avoid truncation
        dialog.border_title = f"Job: {self._job.job_id}"

        # Build and display content
        content = self._build_content()
        text_area = self.query_one("#job-details-content", TextArea)
        text_area.load_text(content)
        text_area.focus()

    def _build_content(self) -> str:
        """Build the formatted job details content."""
        job = self._job
        lines: list[str] = []
        resources = self._extra.get("resources", {})

        # Section: Basic Info
        lines.append("═══ Basic Information ═══")
        lines.append("")
        lines.append(f"  Job ID:      {job.job_id}")
        lines.append(f"  Name:        {job.name}")
        lines.append(f"  User:        {job.user}")
        lines.append(f"  Status:      {job.status.name}")
        lines.append(f"  Queue:       {job.queue or '—'}")
        lines.append(f"  Node:        {job.node or '—'}")
        lines.append("")

        # Section: Command
        job_args = self._extra.get("job_args", [])
        script = self._extra.get("script_file")
        command = self._extra.get("command")  # For qrsh interactive jobs
        if job_args or script or command:
            lines.append("═══ Command ═══")
            lines.append("")
            if command:
                # Interactive job command (from QRSH_COMMAND)
                lines.append(f"  Command:     {command}")
            elif script:
                lines.append(f"  Script:      {script}")
                if job_args:
                    lines.append(f"  Arguments:   {' '.join(job_args)}")
            lines.append("")

        # Section: Timing
        lines.append("═══ Timing ═══")
        lines.append("")
        if job.submit_time:
            lines.append(f"  Submitted:   {job.submit_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            lines.append("  Submitted:   —")
        if job.start_time:
            lines.append(f"  Started:     {job.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            lines.append("  Started:     —")
        if job.end_time:
            lines.append(f"  Ended:       {job.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Runtime:     {job.runtime_display}")
        lines.append("")

        # Section: Resources
        lines.append("═══ Resources ═══")
        lines.append("")

        # Slots from PE
        pe_name = self._extra.get("pe_name")
        pe_range = self._extra.get("pe_range")
        if pe_name:
            lines.append(f"  PE:          {pe_name} ({pe_range or job.cpu or '?'} slots)")
        else:
            lines.append(f"  Slots/CPUs:  {job.cpu or '—'}")

        # Memory - check resources dict for common memory keys
        memory = job.memory
        if not memory:
            for key in ("h_vmem", "mem_free", "virtual_free", "mem", "memory"):
                if key in resources:
                    memory = resources[key]
                    break
        if memory:
            lines.append(f"  Memory:      {memory}")

        # GPU
        if job.gpu:
            lines.append(f"  GPUs:        {job.gpu}")

        # All requested resources
        if resources:
            lines.append("")
            lines.append("  All Requested Resources:")
            for name, value in sorted(resources.items()):
                lines.append(f"    {name}: {value}")
        lines.append("")

        # Section: Paths
        lines.append("═══ Paths ═══")
        lines.append("")
        cwd = self._extra.get("cwd")
        if cwd:
            lines.append(f"  Working Dir: {cwd}")
        lines.append(f"  Stdout:      {job.stdout_path or '—'}")
        lines.append(f"  Stderr:      {job.stderr_path or '—'}")
        lines.append("")

        # Section: Dependencies
        deps = self._extra.get("dependencies", [])
        if deps or job.dependencies:
            lines.append("═══ Dependencies ═══")
            lines.append("")
            all_deps = deps or job.dependencies or []
            if all_deps:
                for dep in all_deps:
                    lines.append(f"  • {dep}")
            else:
                lines.append("  None")
            lines.append("")

        # Section: Array Job Info
        if job.array_task_id is not None:
            lines.append("═══ Array Job ═══")
            lines.append("")
            lines.append(f"  Task ID:     {job.array_task_id}")
            lines.append("")

        # Section: Other
        project = self._extra.get("project")
        department = self._extra.get("department")
        if project or department:
            lines.append("═══ Other ═══")
            lines.append("")
            if project:
                lines.append(f"  Project:     {project}")
            if department:
                lines.append(f"  Department:  {department}")
            lines.append("")

        return "\n".join(lines)

    def action_close(self) -> None:
        """Close the details viewer."""
        self.dismiss(None)

    def action_go_top(self) -> None:
        """Scroll to top."""
        text_area = self.query_one("#job-details-content", TextArea)
        text_area.cursor_location = (0, 0)

    def action_go_bottom(self) -> None:
        """Scroll to bottom."""
        text_area = self.query_one("#job-details-content", TextArea)
        text_area.cursor_location = (len(text_area.document.lines) - 1, 0)

    def action_screenshot(self) -> None:
        """Save a screenshot."""
        path = self.app.save_screenshot(path="./")
        self.app.notify(f"Screenshot saved: {path}", timeout=3)
