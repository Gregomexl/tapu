import asyncio
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import ItemGrid, VerticalScroll
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
    DashboardScreen > VerticalScroll {
        height: 1fr;
    }
    DashboardScreen .splash {
        width: 100%;
        padding: 1 2;
        color: $success;
        overflow: hidden;
        text-align: center;
        content-align: center middle;
    }
    DashboardScreen .cards-grid {
        width: 100%;
        height: auto;
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
        with VerticalScroll():
            yield Static(self.SPLASH, classes="splash")
            yield ItemGrid(id="cards-grid", classes="cards-grid", min_column_width=26)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_all())
        self._refresh_timer = self.set_interval(60, self._tick_refresh)

    def _tick_refresh(self) -> None:
        self._bg_refresh()

    @work(exit_on_error=False)
    async def _bg_refresh(self) -> None:
        await self._load_all()

    async def _fetch_one(self, league: League, grid: ItemGrid) -> None:
        try:
            sb = await self.client.get_scoreboard(league.slug)
        except Exception:
            await grid.mount(Static(f"[red]{league.name}: unavailable[/red]"))
            return
        self._scoreboards[league.slug] = sb
        card_id = f"card-{league.slug.replace('.', '-')}"
        old = grid.query(f"#{card_id}")
        card = LeagueCard(league, sb, self.client, id=card_id)
        if old:
            await old.first().remove()
        await grid.mount(card)

    async def _load_all(self) -> None:
        grid = self.query_one("#cards-grid", ItemGrid)
        if not self._scoreboards:
            await grid.remove_children()
        await asyncio.gather(*[self._fetch_one(l, grid) for l in self.leagues])
        cards = list(grid.query(LeagueCard))
        if cards:
            cards[0].focus()

    def action_refresh(self) -> None:
        self.client.clear_cache()
        self._scoreboards.clear()
        self.run_worker(self._load_all())

    def on_league_card_selected(self, message: LeagueCard.Selected) -> None:
        from tapu.screens.league import LeagueScreen
        sb = self._scoreboards.get(message.league.slug, {})
        self.app.push_screen(LeagueScreen(self.client, message.league, sb))
