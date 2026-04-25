from typing import ClassVar
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from tapu.api import ESPNClient
from tapu.config import League
from tapu.widgets.match_card import MatchCard
from tapu.widgets.standings import StandingsTable


class LeagueScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,b", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "app.open_chat", "Chat"),
    ]

    DEFAULT_CSS = """
    LeagueScreen .matches-pane {
        height: 60%;
        padding: 1;
    }
    LeagueScreen .standings-pane {
        height: 40%;
        padding: 1;
    }
    LeagueScreen .no-matches {
        padding: 2;
        color: $text-muted;
    }
    """

    def __init__(
        self, client: ESPNClient, league: League, scoreboard: dict
    ) -> None:
        super().__init__()
        self.client = client
        self.league = league
        self._scoreboard = scoreboard
        self._standings: dict = {}
        self._refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Scores + Table", id="scores-tab"):
                with Vertical():
                    yield VerticalScroll(id="matches-pane", classes="matches-pane")
                    yield VerticalScroll(id="standings-pane", classes="standings-pane")
            with TabPane("Schedule", id="schedule-tab"):
                yield Static("[dim]Schedule coming soon[/dim]", classes="no-matches")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.league.full_name
        self._render_matches()
        self.run_worker(self._load_standings(), exclusive=True)
        self._refresh_timer = self.set_interval(30, self._auto_refresh)

    def _render_matches(self) -> None:
        pane = self.query_one("#matches-pane", VerticalScroll)
        pane.remove_children()
        events = self._scoreboard.get("events", [])
        if not events:
            pane.mount(Static("[dim]No matches today[/dim]", classes="no-matches"))
            return
        for event in events:
            pane.mount(MatchCard(event))

    async def _load_standings(self) -> None:
        try:
            self._standings = await self.client.get_standings(self.league.slug)
            pane = self.query_one("#standings-pane", VerticalScroll)
            pane.remove_children()
            await pane.mount(StandingsTable(self._standings))
        except Exception:
            pane = self.query_one("#standings-pane", VerticalScroll)
            pane.remove_children()
            await pane.mount(Static("[red]Standings unavailable[/red]"))

    async def _auto_refresh(self) -> None:
        try:
            self._scoreboard = await self.client.get_scoreboard(self.league.slug)
            self._render_matches()
            await self._load_standings()
        except Exception:
            pass

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self.run_worker(self._auto_refresh(), exclusive=True)

    def on_match_card_selected(self, message: MatchCard.Selected) -> None:
        from tapu.screens.match import MatchScreen
        events = self._scoreboard.get("events", [])
        event = next((e for e in events if e["id"] == message.event_id), None)
        if event:
            self.app.push_screen(MatchScreen(self.client, self.league, message.event_id, event))
