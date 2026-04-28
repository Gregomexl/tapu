from io import BytesIO
from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from tapu.api import ESPNClient


def _extract_logo_url(logo_data: Any) -> str | None:
    if isinstance(logo_data, str):
        return logo_data
    if isinstance(logo_data, list) and logo_data:
        entry = logo_data[0]
        return entry.get("href") or entry.get("url")
    return None


def _make_pixels(img_bytes: bytes, w: int, h: int):
    try:
        from PIL import Image
        from rich_pixels import Pixels
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")
        img = img.resize((w, h), Image.LANCZOS)
        return Pixels.from_image(img)
    except Exception:
        return None


class TeamLogo(Widget):
    """Async-loading pixel logo from an ESPN image URL."""

    DEFAULT_CSS = """
    TeamLogo {
        width: auto;
        height: auto;
    }
    """

    def __init__(
        self,
        logo_data: Any,
        client: ESPNClient,
        px_width: int = 12,
        px_height: int = 12,
    ) -> None:
        super().__init__()
        self._url = _extract_logo_url(logo_data)
        self._client = client
        self._px_w = px_width
        self._px_h = px_height
        # half-block chars: 1 terminal line = 2 pixel rows
        self._lines = max(1, px_height // 2)

    def compose(self) -> ComposeResult:
        yield Static("", id="logo-static")

    def on_mount(self) -> None:
        # Reserve space immediately so layout doesn't collapse before image loads
        self.styles.width = self._px_w
        self.styles.height = self._lines
        if self._url:
            self.run_worker(self._load(), exclusive=True)

    @staticmethod
    def _small_url(url: str) -> str:
        return url.replace("/500/", "/50/") if "/500/" in url else url

    async def _load(self) -> None:
        small = self._small_url(self._url)
        img_bytes = None
        # Try the small URL first; fall back to original if it fails
        try:
            img_bytes = await self._client.get_logo_bytes(small)
        except Exception:
            pass
        if img_bytes is None and small != self._url:
            try:
                img_bytes = await self._client.get_logo_bytes(self._url)
            except Exception:
                pass
        if img_bytes is None:
            return
        pixels = _make_pixels(img_bytes, self._px_w, self._px_h)
        if pixels is not None:
            try:
                self.query_one("#logo-static", Static).update(pixels)
            except Exception:
                pass
