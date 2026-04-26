from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _status_display(event: dict) -> str:
    status = event["status"]["type"]
    state = status.get("state", "pre")
    detail = status.get("detail", "")
    clock = event["status"].get("displayClock", "")

    if state == "in":
        return f"[green]● LIVE {clock}[/green]"
    if state == "post":
        return f"[dim]{detail or 'FT'}[/dim]"
    return f"[dim]{detail or 'Upcoming'}[/dim]"


def _format_scorers(key_events: list[dict]) -> str:
    goals = [k for k in key_events if k.get("scoringPlay")]
    if not goals:
        return "[dim]No goals yet[/dim]"
    lines = []
    for g in goals:
        team = g.get("team", {}).get("displayName", "")
        clock = g.get("clock", {}).get("displayValue", "")
        short_text = g.get("shortText", g.get("text", "Goal"))
        lines.append(f"  ⚽ [bold]{clock}[/bold]  {short_text}  [dim]{team}[/dim]")
    return "\n".join(lines)


class MatchDetail(Widget):
    DEFAULT_CSS = """
    MatchDetail {
        height: auto;
        padding: 1 2;
    }
    MatchDetail .section-title {
        color: $primary;
        text-style: bold;
        margin: 1 0 0 0;
    }
    """

    def __init__(self, event: dict[str, Any], summary: dict[str, Any]) -> None:
        super().__init__()
        self.event = event
        self.summary = summary

    def compose(self) -> ComposeResult:
        competitors = self.event["competitions"][0]["competitors"]
        home = _get_team(competitors, "home")
        away = _get_team(competitors, "away")
        home_score = home.get("score", "-")
        away_score = away.get("score", "-")
        home_name = home["team"]["displayName"]
        away_name = away["team"]["displayName"]

        status_str = _status_display(self.event)

        yield Static(
            f"[bold]{home_name}[/bold]  {home_score} - {away_score}  [bold]{away_name}[/bold]\n"
            f"  {status_str}"
        )

        key_events = self.summary.get("keyEvents", [])
        yield Static("Goal Scorers", classes="section-title")
        yield Static(_format_scorers(key_events))

        boxscore = self.summary.get("boxscore", {})
        teams = boxscore.get("teams", [])
        if teams:
            yield Static("Stats", classes="section-title")
            for team_data in teams:
                team_name = team_data.get("team", {}).get("abbreviation", "?")
                stats = team_data.get("statistics", [])
                stat_lines = [
                    f"  {s.get('label', s['name'])}: {s['displayValue']}"
                    for s in stats[:6]
                ]
                yield Static(f"[bold]{team_name}[/bold]\n" + "\n".join(stat_lines))
