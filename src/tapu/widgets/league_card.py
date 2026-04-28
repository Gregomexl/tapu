from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from tapu.api import ESPNClient
from tapu.config import League


class LeagueCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "Open League", show=False),
    ]

    DEFAULT_CSS = """
    LeagueCard {
        height: 6;
        width: 1fr;
        min-width: 24;
        padding: 1 1;
        margin: 0 1 1 0;
        border: solid $surface-lighten-2;
    }
    LeagueCard:hover {
        background: $surface-lighten-1;
    }
    LeagueCard:focus {
        border: solid $primary;
        background: $surface-lighten-2;
    }
    LeagueCard.has-live {
        border: solid $success;
    }
    LeagueCard.has-live:focus {
        border: solid $success;
        background: $surface-lighten-2;
    }
    """

    def __init__(
        self,
        league: League,
        scoreboard: dict[str, Any],
        client: ESPNClient | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.league = league
        self.scoreboard = scoreboard
        self._client = client
        events = scoreboard.get("events", [])
        self.live_count = sum(
            1 for e in events
            if e["status"]["type"].get("state") == "in"
        )
        if self.live_count > 0:
            self.add_class("has-live")

    def compose(self) -> ComposeResult:
        events = self.scoreboard.get("events", [])
        total = len(events)
        if self.live_count > 0:
            match_label = f"[bold green]{self.live_count} live[/bold green][dim] · {total} today[/dim]"
        elif total > 0:
            match_label = f"[dim]{total} matches today[/dim]"
        else:
            match_label = "[dim]No matches today[/dim]"

        flag = f"{self.league.flag}  " if self.league.flag else ""
        yield Static(f"{flag}[bold]{self.league.full_name}[/bold]")
        yield Static(match_label)

    def on_mount(self) -> None:
        self.styles.border_left = ("thick", self.league.color)

    def action_select(self) -> None:
        self.post_message(self.Selected(self.league))

    def on_click(self) -> None:
        self.post_message(self.Selected(self.league))

    class Selected(Message):
        def __init__(self, league: League) -> None:
            super().__init__()
            self.league = league
