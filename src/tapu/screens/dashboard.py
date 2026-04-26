import asyncio
from typing import ClassVar
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import ItemGrid
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static

from tapu.api import ESPNClient
from tapu.config import League
from tapu.widgets.league_card import LeagueCard


class DashboardScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("r", "refresh", "Refresh"),
        Binding("q", "app.quit", "Quit"),
        Binding("?", "app.open_chat", "Chat"),
        Binding("up", "app.focus_previous", "Prev", show=False),
        Binding("left", "app.focus_previous", "Prev", show=False),
        Binding("down", "app.focus_next", "Next", show=False),
        Binding("right", "app.focus_next", "Next", show=False),
    ]

    DEFAULT_CSS = """
    DashboardScreen .splash {
        width: 100%;
        padding: 1 2;
        color: $success;
    }
    DashboardScreen .cards-grid {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    """

    SPLASH = """\
  ████████╗ █████╗ ██████╗ ██╗   ██╗
  ╚══██╔══╝██╔══██╗██╔══██╗██║   ██║
     ██║   ███████║██████╔╝██║   ██║
     ██║   ██╔══██║██╔═══╝ ██║   ██║
     ██║   ██║  ██║██║     ╚██████╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝  ⚽"""

    def __init__(self, client: ESPNClient, leagues: list[League]) -> None:
        super().__init__()
        self.client = client
        self.leagues = leagues
        self._scoreboards: dict[str, dict] = {}
        self._refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.SPLASH, classes="splash")
        yield ItemGrid(id="cards-grid", classes="cards-grid")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_all(), exclusive=True)
        self._refresh_timer = self.set_interval(60, self._auto_refresh)

    async def _fetch_one(self, league: League) -> tuple[League, dict | None]:
        try:
            sb = await self.client.get_scoreboard(league.slug)
            return league, sb
        except Exception:
            return league, None

    async def _load_all(self) -> None:
        grid = self.query_one("#cards-grid", ItemGrid)
        await grid.remove_children()
        results = await asyncio.gather(*[self._fetch_one(l) for l in self.leagues])
        first_card: LeagueCard | None = None
        for league, sb in results:
            if sb is None:
                await grid.mount(Static(f"[red]{league.name}: unavailable[/red]"))
                continue
            self._scoreboards[league.slug] = sb
            card = LeagueCard(league, sb)
            await grid.mount(card)
            if first_card is None:
                first_card = card
        if first_card is not None:
            first_card.focus()

    async def _auto_refresh(self) -> None:
        self.run_worker(self._load_all(), exclusive=True)

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self.run_worker(self._load_all(), exclusive=True)

    def on_league_card_selected(self, message: LeagueCard.Selected) -> None:
        from tapu.screens.league import LeagueScreen
        sb = self._scoreboards.get(message.league.slug, {})
        self.app.push_screen(LeagueScreen(self.client, message.league, sb))
