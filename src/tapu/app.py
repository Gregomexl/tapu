from typing import ClassVar

from textual.app import App
from textual.binding import Binding, BindingType

from tapu.api import ESPNClient
from tapu.config import load_leagues

SPLASH = """\
  ████████╗ █████╗ ██████╗ ██╗   ██╗
  ╚══██╔══╝██╔══██╗██╔══██╗██║   ██║
     ██║   ███████║██████╔╝██║   ██║
     ██║   ██╔══██║██╔═══╝ ██║   ██║
     ██║   ██║  ██║██║     ╚██████╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝  ⚽
  [dim]fútbol en tu terminal[/dim]"""


class TapuApp(App):
    TITLE = "Tapú"
    SUB_TITLE = "fútbol en tu terminal"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("g", "open_palette", "Go to league"),
        Binding("?", "open_help", "Help"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }
    .splash {
        width: 100%;
        height: auto;
        padding: 1 2;
        color: $success;
        text-align: left;
    }
    """

    def __init__(self, refresh_interval: int = 60) -> None:
        super().__init__()
        self.client = ESPNClient()
        self.leagues = load_leagues()
        self.refresh_interval = refresh_interval

    def on_mount(self) -> None:
        from tapu.screens.dashboard import DashboardScreen
        self.push_screen(DashboardScreen(self.client, self.leagues))

    async def on_unmount(self) -> None:
        await self.client.aclose()

    def action_open_palette(self) -> None:
        from tapu.screens.league_palette import LeaguePaletteScreen

        def _on_league_selected(league) -> None:
            if league is None:
                return
            from tapu.screens.dashboard import DashboardScreen
            from tapu.screens.league import LeagueScreen
            # Pop until DashboardScreen is on top so no stale screen remains
            while len(self.screen_stack) > 1 and not isinstance(
                self.screen_stack[-1], DashboardScreen
            ):
                self.pop_screen()
            self.push_screen(LeagueScreen(self.client, league, {}))

        self.push_screen(LeaguePaletteScreen(self.leagues), _on_league_selected)

    def action_open_help(self) -> None:
        from tapu.screens.help import HelpScreen
        bindings = [
            b for b in (*self.BINDINGS, *self.screen.BINDINGS)
            if isinstance(b, Binding)
        ]
        self.push_screen(HelpScreen(bindings))
