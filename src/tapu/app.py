from textual.app import App

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

    def action_open_chat(self) -> None:
        from tapu.screens.chat import ChatScreen
        self.push_screen(ChatScreen())
