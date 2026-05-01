from datetime import datetime
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.reactive import reactive
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


def _period_label(event: dict) -> str:
    """Coarse period label — '1st', '2nd', 'ET', or '' — derived from status.period
    with a fallback to status.type.name. Avoids the ticking-clock complexity since
    ESPN's displayClock can drift between fetches and is fragile around stoppage time.
    """
    status = event.get("status", {})
    name = status.get("type", {}).get("name", "").upper()
    period = status.get("period", 0)
    if "FIRST_HALF" in name or period == 1:
        return "1st"
    if "SECOND_HALF" in name or period == 2:
        return "2nd"
    if "EXTRA" in name or "OVERTIME" in name or period >= 3:
        return "ET"
    return ""


def format_live_status(event: dict, pulse_on: bool = True) -> str:
    """Status badge for in/post states — shared across MatchCard, MatchDetail, MatchScreen.

    Returns "" for pre-match; callers render their own pre-match label.
    """
    status = event["status"]["type"]
    state = status.get("state", "pre")
    if state == "in":
        name = status.get("name", "").upper()
        is_ht = "HALFTIME" in name or "HALF_TIME" in name
        dot = "[green]●[/green]" if pulse_on else " "
        if is_ht:
            return f"{dot} [bold yellow]HT[/bold yellow]"
        period = _period_label(event)
        suffix = f" {period}" if period else ""
        return f"{dot} [bold red]LIVE{suffix}[/bold red]"
    if state == "post":
        return f"[dim]{status.get('detail', 'FT')}[/dim]"
    return ""


def _status_label(event: dict, pulse_on: bool = True) -> str:
    state = event["status"]["type"].get("state", "pre")
    if state in ("in", "post"):
        return format_live_status(event, pulse_on)
    date_str = event.get("date", "")
    local_time = _format_local_time(date_str) if date_str else event["status"]["type"].get("detail", "")
    return f"[cyan]{local_time}[/cyan]"


class MatchCard(Widget, can_focus=True):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select", "View Match", show=False),
        Binding("up", "focus_previous", "", show=False),
        Binding("down", "focus_next", "", show=False),
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
    MatchCard.--flashing {
        border: tall $success;
        background: $success 10%;
    }
    MatchCard.--flashing #line1 {
        color: $success;
        text-style: bold;
    }
    """

    _pulse_on: reactive[bool] = reactive(True)

    def __init__(
        self,
        event: dict[str, Any],
        client: ESPNClient | None = None,
        positions: dict[str, int] | None = None,
        flash: bool = False,
    ) -> None:
        super().__init__()
        self.event = event
        self._client = client
        self._positions = positions or {}
        self._flash = flash
        competitors = event["competitions"][0]["competitors"]
        self._home = _get_team(competitors, "home")
        self._away = _get_team(competitors, "away")
        status_type = event["status"]["type"]
        state = status_type.get("state", "pre")
        name = status_type.get("name", "")
        self._is_ht = state == "in" and ("HALFTIME" in name.upper() or "HALF_TIME" in name.upper())
        self.is_live = state == "in"
        if self.is_live and not self._is_ht:
            self.add_class("live")

    def _render_line1(self) -> str:
        home_abbr = self._home["team"].get("shortDisplayName") or self._home["team"]["abbreviation"]
        away_abbr = self._away["team"].get("shortDisplayName") or self._away["team"]["abbreviation"]
        home_score = self._home.get("score", "-")
        away_score = self._away.get("score", "-")
        status = _status_label(self.event, self._pulse_on)
        return f"[bold]{home_abbr}[/bold]  {home_score} – {away_score}  [bold]{away_abbr}[/bold]  {status}"

    def watch__pulse_on(self, value: bool) -> None:
        try:
            self.query_one("#line1", Static).update(self._render_line1())
        except Exception:
            pass

    def on_mount(self) -> None:
        if self._flash:
            self.add_class("--flashing")
            self.set_timer(3.0, lambda: self.remove_class("--flashing"))
        if self.is_live and not self._is_ht:
            self._pulse_timer = self.set_interval(0.7, self._toggle_pulse)

    def on_unmount(self) -> None:
        if hasattr(self, "_pulse_timer"):
            self._pulse_timer.stop()

    def _toggle_pulse(self) -> None:
        self._pulse_on = not self._pulse_on

    def compose(self) -> ComposeResult:
        yield Static(self._render_line1(), id="line1")
        venue = self.event["competitions"][0].get("venue", {})
        stadium = venue.get("fullName", "")
        city = venue.get("address", {}).get("city", "")
        location = f"{stadium}, {city}" if stadium and city else stadium or city
        notes = self.event["competitions"][0].get("notes", [])
        group = notes[0].get("headline", "") if notes else ""
        second_line = "  ".join(filter(None, [group, f"[dim]{location}[/dim]" if location else ""]))
        if second_line:
            yield Static(f"[dim]{second_line}[/dim]")

    def action_select(self) -> None:
        self.post_message(self.Selected(self.event["id"], self.event))

    def action_focus_previous(self) -> None:
        self.screen.focus_previous()

    def action_focus_next(self) -> None:
        self.screen.focus_next()

    class Selected(Message):
        def __init__(self, event_id: str, event: dict) -> None:
            super().__init__()
            self.event_id = event_id
            self.event = event
