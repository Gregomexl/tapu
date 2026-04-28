from datetime import datetime
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from tapu.api import ESPNClient


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _format_local_time(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%H:%M %Z")
    except Exception:
        return date_str


def _status_label(event: dict) -> str:
    status = event["status"]["type"]
    state = status.get("state", "pre")
    if state == "in":
        name = status.get("name", "")
        if "HALFTIME" in name.upper() or "HALF_TIME" in name.upper():
            return "[yellow]● HT[/yellow]"
        period = event["status"].get("period", 1)
        if period >= 2:
            clock = event["status"].get("displayClock", "")
            suffix = f" {clock}" if clock else ""
            return f"[green]● LIVE{suffix}[/green]"
        return "[green]● LIVE[/green]"
    if state == "post":
        return f"[dim]{status.get('detail', 'FT')}[/dim]"
    date_str = event.get("date", "")
    local_time = _format_local_time(date_str) if date_str else status.get("detail", "")
    return f"[dim]{local_time}[/dim]"


class MatchCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "View Match", show=False),
    ]

    DEFAULT_CSS = """
    MatchCard {
        height: auto;
        padding: 1 1;
        margin: 0 0 1 0;
        border: solid $surface-lighten-2;
    }
    MatchCard:hover {
        background: $surface-lighten-1;
    }
    MatchCard:focus {
        border: solid $primary;
        background: $surface-lighten-2;
    }
    MatchCard.live {
        border: solid $success;
        background: $surface-darken-1;
    }
    MatchCard.live:focus {
        border: solid $success;
        background: $surface-lighten-2;
    }
    """

    def __init__(self, event: dict[str, Any], client: ESPNClient | None = None, positions: dict[str, int] | None = None) -> None:
        super().__init__()
        self.event = event
        self._client = client
        self._positions = positions or {}
        competitors = event["competitions"][0]["competitors"]
        self._home = _get_team(competitors, "home")
        self._away = _get_team(competitors, "away")
        self.is_live = event["status"]["type"].get("state") == "in"
        if self.is_live:
            self.add_class("live")

    def compose(self) -> ComposeResult:
        home_abbr = self._home["team"].get("shortDisplayName") or self._home["team"]["abbreviation"]
        away_abbr = self._away["team"].get("shortDisplayName") or self._away["team"]["abbreviation"]
        home_score = self._home.get("score", "-")
        away_score = self._away.get("score", "-")
        status = _status_label(self.event)


        venue = self.event["competitions"][0].get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        location = f"{stadium}, {city}" if stadium and city else stadium or city

        notes = self.event["competitions"][0].get("notes", [])
        group = notes[0].get("headline", "") if notes else ""

        yield Static(
            f"[bold]{home_abbr}[/bold]  {home_score} – {away_score}  [bold]{away_abbr}[/bold]  {status}"
        )
        second_line = "  ".join(filter(None, [group, f"[dim]{location}[/dim]" if location else ""]))
        if second_line:
            yield Static(f"[dim]{second_line}[/dim]")

    def action_select(self) -> None:
        self.post_message(self.Selected(self.event["id"], self.event))

    class Selected(Message):
        def __init__(self, event_id: str, event: dict) -> None:
            super().__init__()
            self.event_id = event_id
            self.event = event
