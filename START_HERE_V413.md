# VikaTennis v4.13 — START HERE

## Goal
This is the first release intended for everyday use without waiting for the historical/live research pipeline to finish.

Bundled production artifacts:
- V4.2 leakage-safe pre-match model
- player state through 2025-12-29
- 2015–2025 archive
- V4.5 live fallback + 100k remainder Monte Carlo
- optional V4.7 live ML artifact when trained

## 1. Install

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements_v47.txt
```

## 2. Configure

Copy `.env.example` to `.env` and set:

```text
TELEGRAM_BOT_TOKEN=...
LIVETENNISAPI_KEY=...
```

`TELEGRAM_BOT_TOKEN` is required. `LIVETENNISAPI_KEY` is optional but strongly recommended for live matches.

## 3. Check

```bash
python scripts_v413_healthcheck.py
```

## 4. Start

```bash
python start_bot.py
```

Telegram commands:
- `/predict Player1 Player2 hard`
- `/form Player`
- `/h2h Player1 Player2`
- `/live`
- `/live MATCH_ID`
- `/errors`

## Important
The bundled player state ends on 2025-12-29. The bot is usable now, but the pre-match state is not yet refreshed with all 2026 completed matches. Adding a Live Tennis API key enables current live data. The next production upgrade is the 2026 rolling-state sync, followed by historical live Champion training.
