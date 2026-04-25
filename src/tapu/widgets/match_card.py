from typing import Any, ClassVar
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widgets import Static
from textual.widget import Widget


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _status_label(event: dict) -> str:
    status_name = event["status"]["type"]["name"]
    if status_name == "STATUS_IN_PROGRESS":
        clock = event["status"].get("displayClock", "")
        return f"[green]● LIVE {clock}[/green]"
    if status_name == "STATUS_FINAL":
        return "[dim]FT[/dim]"
    return "[dim]Upcoming[/dim]"


class MatchCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "View Match", show=False),
    ]

    DEFAULT_CSS = """
    MatchCard {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: solid $surface-lighten-2;
    }
    MatchCard:focus {
        border: solid $primary;
    }
    MatchCard.live {
        border: solid $success;
    }
    """

    def __init__(self, event: dict[str, Any]) -> None:
        super().__init__()
        self.event = event
        competitors = event["competitions"][0]["competitors"]
        self._home = _get_team(competitors, "home")
        self._away = _get_team(competitors, "away")
        self.is_live = event["status"]["type"]["name"] == "STATUS_IN_PROGRESS"
        if self.is_live:
            self.add_class("live")

    def compose(self) -> ComposeResult:
        home_abbr = self._home["team"]["abbreviation"]
        away_abbr = self._away["team"]["abbreviation"]
        home_score = self._home.get("score", "-")
        away_score = self._away.get("score", "-")
        status = _status_label(self.event)
        yield Static(
            f"[bold]{home_abbr}[/bold] {home_score} - {away_score} [bold]{away_abbr}[/bold]"
            f"  {status}"
        )

    def action_select(self) -> None:
        self.post_message(self.Selected(self.event["id"]))

    class Selected(Message):
        def __init__(self, event_id: str) -> None:
            super().__init__()
            self.event_id = event_id
