# Tapú ⚽

> *fútbol en tu terminal*

Tapú (from Zapotec: *tapu'*, the ancient Mesoamerican ball game) is a terminal TUI for live soccer stats — no browser needed.

```
  ████████╗ █████╗ ██████╗ ██╗   ██╗
  ╚══██╔══╝██╔══██╗██╔══██╗██║   ██║
     ██║   ███████║██████╔╝██║   ██║
     ██║   ██╔══██║██╔═══╝ ██║   ██║
     ██║   ██║  ██║██║     ╚██████╔╝
     ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝  ⚽
```

## Features

- Live scoreboards for UCL, UEL, Premier League, La Liga, FIFA World Cup, Liga MX
- League standings tables
- Match detail: scorers, stats, lineups
- Config-driven — add any ESPN league with one line in `leagues.toml`
- Powered by the public ESPN API (no API key required)

## Install

```bash
uv tool install tapu
```

Or run directly:

```bash
uvx tapu
```

## Usage

```bash
tapu        # Launch TUI
```

### Key Bindings

| Key | Action |
|-----|--------|
| `↑↓←→` | Navigate |
| `Enter` | Select / drill down |
| `Esc` / `b` | Back |
| `r` | Refresh |
| `?` | Chat (v2) |
| `q` | Quit |

## Adding Leagues

Edit `leagues.toml`:

```toml
[[leagues]]
slug = "ita.1"
name = "Serie A"
full_name = "Serie A"
```

## Requirements

- Python 3.13+
- [chafa](https://hpjansson.org/chafa/) (optional — for team logos in match detail)

## License

MIT
