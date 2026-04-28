# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv run tapu              # Run the TUI
uv run pytest            # Run all tests
uv run pytest tests/test_config.py::test_name -v   # Run a single test
uv run ruff check src    # Lint
uv run ruff format src   # Format
```

## Architecture

**Entry point:** `src/tapu/cli.py` → `TapuApp` (in `app.py`) → pushes `DashboardScreen` on mount.

**Screen stack (Textual):** Screens are pushed/popped via `app.push_screen` / `app.pop_screen`. The flow is:
`DashboardScreen` (league cards grid) → `LeagueScreen` (matches + standings) → `MatchScreen` (match detail)

**Config:** `leagues.toml` at repo root defines all leagues. `src/tapu/config.py` loads it into frozen `League` dataclasses. Adding a league is a one-line TOML entry — no code changes needed. The `related` field (list of `{name, slug}` inline tables) drives tournament tabs in `LeagueScreen`.

**API client** (`src/tapu/api/client.py`): `ESPNClient` wraps the public ESPN API with a two-layer cache — in-memory (30s TTL) and disk (`~/.cache/tapu/`, configurable per-call TTL). All methods are `async`. Key methods:
- `get_scoreboard(slug)` — today's matches (in-memory cache)
- `get_scoreboard_daterange(slug, start, end)` — date-range fetch (disk cache, 1h TTL)
- `get_tournament_events(slug)` — full season Aug→Jul (calls `get_scoreboard_daterange`)
- `get_standings(slug)`, `get_match_summary(event_id)`
- `clear_cache()` — clears in-memory cache only (disk cache persists)

**Widgets** live in `src/tapu/widgets/`. Each widget is self-contained. `MatchCard` and `LeagueCard` post `Message` subclasses to communicate with parent screens (Textual message-passing pattern — no direct parent references).

**CSS** is defined inline as `DEFAULT_CSS` class variables on each widget/screen. No external CSS files.

**Tests** use `pytest-asyncio` with `asyncio_mode = "auto"`. Textual widget tests use `app.run_test()` as an async context manager. The `conftest.py` provides `sample_scoreboard` and `sample_standings` fixtures.

## ESPN API Slugs

League slugs (e.g. `esp.1`, `eng.1`) and tournament slugs (e.g. `esp.copa_del_rey`, `eng.fa`) map directly to ESPN's public API at `https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard`. Standings use a different base: `https://site.web.api.espn.com/apis/v2/sports/soccer/{slug}/standings`. Verify new slugs with curl before adding them to `leagues.toml`.
