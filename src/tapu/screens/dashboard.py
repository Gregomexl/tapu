import asyncio
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import ItemGrid, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, LoadingIndicator, Static

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
    DashboardScreen LoadingIndicator {
        height: 3;
        background: transparent;
        color: $success;
    }
    """

    SPLASH = (
        r"""  ████████╗ █████╗ ██████╗ ██╗   ██╗      _,...,_
  ╚══██╔══╝██╔══██╗██╔══██╗██║   ██║    .'@/   \@'.
     ██║   ███████║██████╔╝██║   ██║   //  \___/  \\
     ██║   ██╔══██║██╔═══╝ ██║   ██║  |@\__/a@a\__/a|
     ██║   ██║  ██║██║     ╚██████╔╝  |a/  \@@@/  \@|
     ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝   \\__/   \__//
                                        `.a\___/a.'
                                          `'""" + '""""'
    )

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
            yield LoadingIndicator(id="loader")
            yield ItemGrid(id="cards-grid", classes="cards-grid", min_column_width=40)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_all())
        self._refresh_timer = self.set_interval(60, self._tick_refresh)

    def _tick_refresh(self) -> None:
        self._bg_refresh()

    @work(exit_on_error=False)
    async def _bg_refresh(self) -> None:
        await self._load_all(show_loader=False)

    async def _load_all(self, show_loader: bool = True) -> None:
        loader = self.query_one("#loader", LoadingIndicator)
        grid = self.query_one("#cards-grid", ItemGrid)

        if show_loader:
            loader.display = True

        results = await asyncio.gather(
            *[self.client.get_scoreboard(l.slug) for l in self.leagues],
            return_exceptions=True,
        )
        for league, result in zip(self.leagues, results):
            if not isinstance(result, Exception):
                self._scoreboards[league.slug] = result

        loader.display = False

        await grid.remove_children()
        cards: list = []
        for league in self.leagues:
            card_id = f"card-{league.slug.replace('.', '-')}"
            sb = self._scoreboards.get(league.slug, {})
            cards.append(LeagueCard(league, sb, self.client, id=card_id))
        await grid.mount(*cards)
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
