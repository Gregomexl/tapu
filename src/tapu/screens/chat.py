from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class ChatScreen(Screen):
    BINDINGS: list[BindingType] = [
        Binding("escape,b", "app.pop_screen", "Back", show=True),
    ]

    DEFAULT_CSS = """
    ChatScreen {
        align: center middle;
    }
    ChatScreen .chat-placeholder {
        width: 60;
        height: auto;
        padding: 2 4;
        border: round $primary;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            "[bold]Tapú Chat[/bold]  [dim](coming in v2)[/dim]\n\n"
            "Ask anything about scores, standings, or players.\n"
            "Powered by MCP — install the [italic]tapu-mcp[/italic] plugin to enable.\n\n"
            "[dim]Press Esc to go back[/dim]",
            classes="chat-placeholder",
        )
        yield Footer()
