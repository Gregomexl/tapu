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
    # exact ESPN slug matches first
    _exact = {"final": 0, "semifinals": 1, "quarterfinals": 2, "round-of-16": 3, "round-of-32": 4}
    if h in _exact:
        return _exact[h]
    # headline substring fallback
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
    """Return display-ready round name. Tries notes headline first, falls back to season.slug."""
    notes = event.get("competitions", [{}])[0].get("notes", [])
    if notes:
        headline = notes[0].get("headline", "").strip()
        if headline:
            return headline
    slug = event.get("season", {}).get("slug", "")
    return _SLUG_DISPLAY.get(slug, slug.replace("-", " ").title()) if slug else ""


def _winner_id(event: dict) -> str | None:
    if event.get("status", {}).get("type", {}).get("state") != "post":
        return None
    competitors = event.get("competitions", [{}])[0].get("competitors", [])
    winner = next((c for c in competitors if c.get("winner")), None)
    return str(winner["team"]["id"]) if winner else None


def _fmt_team(comp: dict, width: int = 10) -> str:
    name = (comp["team"].get("shortDisplayName") or comp["team"].get("abbreviation", "?"))[:width]
    score = comp.get("score") or "-"
    return f"{name:<{width}} {score:>2}"


def _get_competitors(event: dict) -> tuple[dict, dict]:
    comps = event["competitions"][0]["competitors"]
    home = next((c for c in comps if c["homeAway"] == "home"), comps[0])
    away = next((c for c in comps if c["homeAway"] == "away"), comps[min(1, len(comps) - 1)])
    return home, away


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

    sorted_rounds = sorted(by_round.items(), key=lambda x: _round_key(x[0]))

    qf_evs: list[dict] = []
    sf_evs: list[dict] = []
    final_evs: list[dict] = []
    for name, evs in sorted_rounds:
        k = _round_key(name)
        if k == 2:
            qf_evs = evs
        elif k == 1:
            sf_evs = evs
        elif k == 0:
            final_evs = evs

    if not sf_evs and not final_evs:
        return ["[dim]Bracket not yet available[/dim]"]

    N = 10
    gap = " " * (N + 3)

    qf_by_winner: dict[str, dict] = {}
    for ev in qf_evs:
        wid = _winner_id(ev)
        if wid:
            qf_by_winner[wid] = ev

    def null_team(width: int = N) -> str:
        return f"{'?':<{width}}  -"

    lines: list[str] = []

    if qf_evs:
        lines.append(f"  {'QUARTERFINALS':<{N + 3}}  SEMIFINALS")
    else:
        lines.append("  SEMIFINALS")
    lines.append("")

    for sf_ev in sf_evs:
        sf_home, sf_away = _get_competitors(sf_ev)
        home_id = str(sf_home["team"]["id"])
        away_id = str(sf_away["team"]["id"])

        qf_for_home = qf_by_winner.get(home_id)
        qf_for_away = qf_by_winner.get(away_id)

        if qf_for_home:
            qh, qa = _get_competitors(qf_for_home)
            lines.append(f"  {_fmt_team(qh, N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_home, N)}")
            lines.append(f"  {_fmt_team(qa, N)} ─┘")
        else:
            lines.append(f"  {null_team(N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_home, N)}")
            lines.append(f"  {null_team(N)} ─┘")

        lines.append("")

        if qf_for_away:
            qh, qa = _get_competitors(qf_for_away)
            lines.append(f"  {_fmt_team(qh, N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_away, N)}")
            lines.append(f"  {_fmt_team(qa, N)} ─┘")
        else:
            lines.append(f"  {null_team(N)} ─┐")
            lines.append(f"  {gap}  ├─ {_fmt_team(sf_away, N)}")
            lines.append(f"  {null_team(N)} ─┘")

        lines.append("")

    lines.append("  " + "─" * 30)
    lines.append("  FINAL")
    lines.append("")

    if final_evs:
        fin_home, fin_away = _get_competitors(final_evs[0])
        state = final_evs[0].get("status", {}).get("type", {}).get("state", "pre")
        if state == "post":
            lines.append(f"  {_fmt_team(fin_home, N)}  –  {_fmt_team(fin_away, N)}")
        elif state == "in":
            lines.append(
                f"  {_fmt_team(fin_home, N)}  [green]LIVE[/green]  {_fmt_team(fin_away, N)}"
            )
        else:
            h_name = (fin_home["team"].get("shortDisplayName") or fin_home["team"].get("abbreviation", "?"))[:N]
            a_name = (fin_away["team"].get("shortDisplayName") or fin_away["team"].get("abbreviation", "?"))[:N]
            lines.append(f"  {h_name:<{N}}  vs  {a_name:<{N}}")
    else:
        finalists: list[str] = []
        for sf_ev in sf_evs:
            wid = _winner_id(sf_ev)
            if wid:
                sf_home, sf_away = _get_competitors(sf_ev)
                comp = sf_home if str(sf_home["team"]["id"]) == wid else sf_away
                finalists.append(
                    (comp["team"].get("shortDisplayName") or comp["team"].get("abbreviation", "?"))[:N]
                )
        if len(finalists) >= 2:
            lines.append(f"  {finalists[0]:<{N}}  vs  {finalists[1]:<{N}}")
        elif len(finalists) == 1:
            lines.append(f"  {finalists[0]:<{N}}  vs  [dim]TBD[/dim]")
        else:
            lines.append("  [dim]TBD[/dim]")

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
