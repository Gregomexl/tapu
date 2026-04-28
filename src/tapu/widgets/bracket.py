from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


_SLUG_DISPLAY: dict[str, str] = {
    "final": "Final",
    "semifinals": "Semifinals",
    "quarterfinals": "Quarterfinals",
    "round-of-16": "Round of 16",
    "round-of-32": "Round of 32",
    "fifth-round": "Fifth Round",
    "fourth-round": "Fourth Round",
    "third-round": "Third Round",
    "second-round": "Second Round",
    "first-round": "First Round",
    "qualifying-round": "Qualifying Round",
    "preliminary-round": "Preliminary Round",
}


def _round_key(headline: str) -> int:
    h = headline.lower().strip()
    _exact = {"final": 0, "semifinals": 1, "quarterfinals": 2, "round-of-16": 3, "round-of-32": 4}
    if h in _exact:
        return _exact[h]
    if h.startswith("final") and "semifinal" not in h and "quarterfinal" not in h:
        return 0
    if "semifinal" in h or "semi-final" in h:
        return 1
    if "quarterfinal" in h or "quarter-final" in h:
        return 2
    if "round of 16" in h:
        return 3
    if "round of 32" in h:
        return 4
    if "fifth" in h:
        return 5
    if "fourth" in h:
        return 6
    if "third" in h:
        return 7
    if "second" in h:
        return 8
    if "first" in h:
        return 9
    return 99


def _event_round(event: dict) -> str:
    """Return display-ready round name. Only uses notes headline when it maps to a known round."""
    notes = event.get("competitions", [{}])[0].get("notes", [])
    if notes:
        headline = notes[0].get("headline", "").strip()
        if headline and _round_key(headline) < 99:
            return headline
    slug = event.get("season", {}).get("slug", "")
    return _SLUG_DISPLAY.get(slug, slug.replace("-", " ").title()) if slug else ""


def _winner_id(event: dict) -> str | None:
    if event.get("status", {}).get("type", {}).get("state") != "post":
        return None
    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    winner = next((c for c in competitors if c.get("winner")), None)
    return str(winner["team"]["id"]) if winner else None


def _team_name(comp: dict, width: int = 16) -> str:
    return (comp["team"].get("shortDisplayName") or comp["team"].get("abbreviation", "?"))[:width]


_ROUND_COLORS = {
    0: "bold yellow",    # Final
    1: "bold cyan",      # Semifinals
    2: "bold green",     # Quarterfinals
    3: "bold blue",      # Round of 16
    4: "bold magenta",   # Round of 32
}


def _round_color(key: int) -> str:
    return _ROUND_COLORS.get(key, "bold white")


def _bracket_lines(events: list[dict]) -> list[str]:
    if not events:
        return ["[dim]Bracket not yet available[/dim]"]

    by_round: dict[str, list[dict]] = {}
    for ev in events:
        r = _event_round(ev)
        if r:
            by_round.setdefault(r, []).append(ev)
    if not by_round:
        return ["[dim]Bracket not yet available[/dim]"]

    has_knockout = any(_round_key(r) < 99 for r in by_round)
    if not has_knockout:
        return ["[dim]Bracket not yet available[/dim]"]

    sorted_rounds = sorted(by_round.items(), key=lambda x: _round_key(x[0]))

    NAME_W = 16
    lines: list[str] = []

    for round_name, round_evs in sorted_rounds:
        key = _round_key(round_name)
        color = _round_color(key)
        sep = "─" * max(0, 40 - len(round_name) - 4)
        lines.append(f"[{color}]── {round_name.upper()} {sep}[/{color}]")
        lines.append("")

        for ev in round_evs:
            comps = ev["competitions"][0]["competitors"]
            home = next((c for c in comps if c["homeAway"] == "home"), comps[0])
            away = next((c for c in comps if c["homeAway"] == "away"), comps[min(1, len(comps) - 1)])

            home_name = _team_name(home, NAME_W)
            away_name = _team_name(away, NAME_W)
            home_score = home.get("score") or "-"
            away_score = away.get("score") or "-"
            state = ev.get("status", {}).get("type", {}).get("state", "pre")
            wid = _winner_id(ev)

            if state == "post":
                home_is_winner = wid == str(home["team"]["id"])
                away_is_winner = wid == str(away["team"]["id"])
                h = f"[bold cyan]{home_name}[/bold cyan]" if home_is_winner else f"[dim]{home_name}[/dim]"
                a = f"[bold cyan]{away_name}[/bold cyan]" if away_is_winner else f"[dim]{away_name}[/dim]"
                score = f"[bold]{home_score}[/bold] [dim]–[/dim] [bold]{away_score}[/bold]"
                winner_name = _team_name(home if home_is_winner else away, NAME_W) if wid else ""
                is_final = _round_key(round_name) == 0
                trophy = "🏆 " if is_final else ""
                arrow = f"  [bold cyan]──► {trophy}{winner_name}[/bold cyan]" if winner_name else ""
                lines.append(f"  {h}  {score}  {a}{arrow}")
            elif state == "in":
                clock = ev.get("status", {}).get("displayClock", "")
                score = f"[bold green]{home_score}[/bold green] [green]●[/green] [bold green]{away_score}[/bold green]"
                time_str = f"[green]{clock}[/green]" if clock else "[green]LIVE[/green]"
                lines.append(f"  [bold]{home_name}[/bold]  {score}  [bold]{away_name}[/bold]  {time_str}")
            else:
                date_str = ev.get("date", "")
                if date_str:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        time_label = dt.astimezone().strftime("%b %-d")
                    except Exception:
                        time_label = ""
                else:
                    time_label = ""
                detail = f"  [dim]{time_label}[/dim]" if time_label else ""
                lines.append(f"  [dim]{home_name}[/dim]  [dim]vs[/dim]  [dim]{away_name}[/dim]{detail}")

        lines.append("")

    return lines


class BracketWidget(Widget):
    DEFAULT_CSS = """
    BracketWidget {
        height: auto;
        width: 100%;
        padding: 1 0;
    }
    """

    def __init__(self, events: list[dict[str, Any]]) -> None:
        super().__init__()
        self._events = events

    def compose(self) -> ComposeResult:
        for line in _bracket_lines(self._events):
            yield Static(line)
