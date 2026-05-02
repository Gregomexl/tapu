import asyncio
from tapu.api.client import ESPNClient

async def main():
    client = ESPNClient()
    sb = await client.get_scoreboard("esp.1")
    for event in sb.get("events", []):
        comps = event["competitions"][0]["competitors"]
        home = next(c for c in comps if c["homeAway"] == "home")["team"]
        away = next(c for c in comps if c["homeAway"] == "away")["team"]
        print(f"{home['displayName']} ({home.get('color')}) vs {away['displayName']} ({away.get('color')})")

asyncio.run(main())
