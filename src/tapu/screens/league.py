from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static

from tapu.api import ESPNClient
from tapu.config import League
from tapu.widgets.match_card import MatchCard
from tapu.widgets.standings import StandingsTable


def _date_to_api(d: date) -> str:
    return d.strftime("%Y%m%d")


def _event_local_date(event: dict) -> date:
    try:
        dt = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
        return dt.astimezone().date()
    except Exception:
        return date.today()


def _group_events_by_day(events: list) -> list[tuple[date, list]]:
    """Return [(day, [events sorted live-first]) ...] sorted newest day first."""
    by_day: dict[date, list] = defaultdict(list)
    for ev in events:
        by_day[_event_local_date(ev)].append(ev)
    result = []
    for d in sorted(by_day.keys(), reverse=True):
        day_evs = by_day[d]
        live = [e for e in day_evs if e["status"]["type"].get("state") == "in"]
        done = [e for e in day_evs if e["status"]["type"].get("state") == "post"]
        pre = [e for e in day_evs if e["status"]["type"].get("state") not in ("in", "post")]
        result.append((d, live + done + pre))
    return result


def _day_label(d: date, today: date) -> str:
    if d == today:
        return f"TODAY  ·  {d.strftime('%a %b %-d, %Y')}"
    if d == today - timedelta(days=1):
        return f"YESTERDAY  ·  {d.strftime('%a %b %-d, %Y')}"
    return d.strftime("%A  ·  %b %-d, %Y")


class LeagueScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("b", "app.pop_screen", "Back", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("m", "more", "More"),
        Binding("?", "app.open_chat", "Chat"),
        Binding("up", "app.focus_previous", "Prev", show=False),
        Binding("down", "app.focus_next", "Next", show=False),
    ]

    DEFAULT_CSS = """
    LeagueScreen .main-row {
        height: 1fr;
    }
    LeagueScreen .matches-col {
        width: 1fr;
        height: 1fr;
        padding: 1;
    }
    LeagueScreen .standings-col {
        width: 56;
        height: 1fr;
        border-left: solid $surface-lighten-2;
        padding: 1 1 1 1;
    }
    LeagueScreen .no-matches {
        padding: 2;
        color: $text-muted;
    }
    LeagueScreen .section-header {
        padding: 0 1;
        margin: 1 0 0 0;
        color: $accent;
        text-style: bold;
        border-left: thick $accent;
    }
    """

    def __init__(self, client: ESPNClient, league: League, scoreboard: dict) -> None:
        super().__init__()
        self.client = client
        self.league = league
        self._days_back = 7
        self._refresh_timer: Timer | None = None
        self._positions: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main-row"):
            yield VerticalScroll(
                Static("[dim]Loading...[/dim]", classes="no-matches"),
                id="matches-pane",
                classes="matches-col",
            )
            yield VerticalScroll(id="standings-pane", classes="standings-col")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.league.full_name
        self.run_worker(self._load_matches())
        self.run_worker(self._load_standings())
        self._refresh_timer = self.set_interval(60, self._tick_refresh)

    def _tick_refresh(self) -> None:
        self._bg_refresh()

    @work(exit_on_error=False)
    async def _bg_refresh(self) -> None:
        await self._load_matches()

    async def _fetch_positions(self) -> dict[str, int]:
        try:
            standings = await self.client.get_standings(self.league.slug)
            positions: dict[str, int] = {}
            for child in standings.get("children", []):
                for i, entry in enumerate(child.get("standings", {}).get("entries", []), 1):
                    positions[str(entry["team"]["id"])] = i
            if not positions:
                for i, entry in enumerate(standings.get("standings", {}).get("entries", []), 1):
                    positions[str(entry["team"]["id"])] = i
            return positions
        except Exception:
            return {}

    async def _load_matches(self) -> None:
        today = date.today()
        start = today - timedelta(days=self._days_back)
        pane = self.query_one("#matches-pane", VerticalScroll)
        try:
            if not self._positions:
                self._positions = await self._fetch_positions()
            sb = await self.client.get_scoreboard_daterange(
                self.league.slug,
                _date_to_api(start),
                _date_to_api(today),
            )
            events = sb.get("events", [])
            await pane.remove_children()
            if not events:
                await pane.mount(Static("[dim]No matches[/dim]", classes="no-matches"))
                return
            for day, day_evs in _group_events_by_day(events):
                await pane.mount(Static(_day_label(day, today), classes="section-header"))
                for ev in day_evs:
                    await pane.mount(MatchCard(ev, positions=self._positions))
        except Exception:
            await pane.remove_children()
            await pane.mount(Static("[red]Failed to load[/red]", classes="no-matches"))

    async def _load_standings(self) -> None:
        pane = self.query_one("#standings-pane", VerticalScroll)
        try:
            standings = await self.client.get_standings(self.league.slug)
            await pane.remove_children()
            await pane.mount(StandingsTable(standings, self.league.relegation_spots))
        except Exception:
            await pane.remove_children()
            await pane.mount(Static("[red]Standings unavailable[/red]"))

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self.run_worker(self._load_matches())
        self.run_worker(self._load_standings())

    def action_more(self) -> None:
        self._days_back += 7
        self.run_worker(self._load_matches())

    def on_match_card_selected(self, message: MatchCard.Selected) -> None:
        from tapu.screens.match import MatchScreen
        self.app.push_screen(
            MatchScreen(self.client, self.league, message.event_id, message.event)
        )
