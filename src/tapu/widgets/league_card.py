from typing import Any, ClassVar
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from tapu.config import League


class LeagueCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "Open League", show=False),
    ]

    DEFAULT_CSS = """
    LeagueCard {
        height: 7;
        width: 1fr;
        min-width: 24;
        padding: 1 2;
        margin: 0 1 1 0;
        border: solid $surface-lighten-2;
    }
    LeagueCard:focus {
        border: solid $primary;
    }
    LeagueCard.has-live {
        border: solid $success;
    }
    """

    def __init__(self, league: League, scoreboard: dict[str, Any]) -> None:
        super().__init__()
        self.league = league
        self.scoreboard = scoreboard
        events = scoreboard.get("events", [])
        self.live_count = sum(
            1 for e in events
            if e["status"]["type"]["name"] == "STATUS_IN_PROGRESS"
        )
        if self.live_count > 0:
            self.add_class("has-live")

    def compose(self) -> ComposeResult:
        events = self.scoreboard.get("events", [])
        live_label = (
            f"[green]{self.live_count} live[/green]"
            if self.live_count > 0
            else f"[dim]{len(events)} matches[/dim]"
        )
        top_match = ""
        if events:
            e = events[0]
            comps = e["competitions"][0]["competitors"]
            home = next(c for c in comps if c["homeAway"] == "home")
            away = next(c for c in comps if c["homeAway"] == "away")
            top_match = (
                f"{home['team']['abbreviation']} "
                f"{home.get('score', '-')}-{away.get('score', '-')} "
                f"{away['team']['abbreviation']}"
            )
        yield Static(f"[bold]{self.league.name}[/bold]  {live_label}")
        yield Static(f"[dim]{self.league.full_name}[/dim]")
        yield Static(top_match or "[dim]No matches today[/dim]")

    def action_select(self) -> None:
        self.post_message(self.Selected(self.league))

    class Selected(Message):
        def __init__(self, league: League) -> None:
            super().__init__()
            self.league = league
