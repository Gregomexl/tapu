from typing import Any
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


def _get_team(competitors: list[dict], home_away: str) -> dict:
    for c in competitors:
        if c["homeAway"] == home_away:
            return c
    return competitors[0]


def _format_scorers(plays: list[dict]) -> str:
    goals = [
        p for p in plays
        if p.get("type", {}).get("id") == "96"
    ]
    if not goals:
        return "[dim]No scorers yet[/dim]"
    lines = []
    for g in goals:
        scorer = g.get("participants", [{}])[0].get("athlete", {}).get("shortName", "?")
        clock = g.get("clock", {}).get("displayValue", "")
        lines.append(f"  ⚽ {scorer} {clock}")
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
        status = self.event["status"]["type"]["name"]
        clock = self.event["status"].get("displayClock", "")

        status_str = {
            "STATUS_IN_PROGRESS": f"[green]● LIVE {clock}[/green]",
            "STATUS_FINAL": "[dim]Full Time[/dim]",
        }.get(status, "[dim]Upcoming[/dim]")

        yield Static(
            f"[bold]{home_name}[/bold]  {home_score} - {away_score}  [bold]{away_name}[/bold]\n"
            f"  {status_str}"
        )

        plays = self.summary.get("plays", [])
        yield Static("Goal Scorers", classes="section-title")
        yield Static(_format_scorers(plays))

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
