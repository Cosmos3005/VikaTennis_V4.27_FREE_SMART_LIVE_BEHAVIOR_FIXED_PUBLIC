# VikaTennis V4.18 — Start Here

1. Copy `.env.example` to `.env`.
2. Set `TELEGRAM_BOT_TOKEN`.
3. For live API: set `LIVETENNISAPI_KEY` (ULTRA for WebSocket/per-point feed).
4. Run `python scripts_v418_healthcheck.py`.
5. Run `python start_bot.py`.

Telegram:
- `/predict Player1 Player2 hard`
- `/form Player`
- `/h2h Player1 Player2`
- `/live`
- `/live MATCH_ID`
- `/status`
- `/model`
- `/errors`

The bot remains usable without the live API for local pre-match predictions. Live WebSocket/per-point functionality activates only when the corresponding API access is configured.
