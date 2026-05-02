from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen):
    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-container {
        width: 68;
        height: auto;
        max-height: 80%;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #help-container VerticalScroll {
        height: auto;
        max-height: 60vh;
        scrollbar-size: 1 1;
    }
    """

    def __init__(self, bindings: list[Binding]) -> None:
        super().__init__()
        self._help_bindings = bindings

    def compose(self) -> ComposeResult:
        visible = [b for b in self._help_bindings if b.show]
        hidden = [b for b in self._help_bindings if not b.show]

        lines: list[str] = ["[bold]Key Bindings[/bold]\n"]
        if visible:
            for b in visible:
                lines.append(f"  [bold cyan]{b.key:<12}[/bold cyan] {b.description}")
        if hidden:
            lines.append("\n[dim]Hidden shortcuts[/dim]")
            for b in hidden:
                lines.append(f"  [dim]{b.key:<12} {b.description}[/dim]")
        if not visible and not hidden:
            lines.append("  [dim]No bindings defined[/dim]")
        lines.append("\n[dim]Press ? or Esc to close[/dim]")

        with Vertical(id="help-container"):
            yield VerticalScroll(Static("\n".join(lines)))

    def on_key(self, event: Key) -> None:
        if event.key in ("escape", "question_mark"):
            self.dismiss()
            event.stop()
