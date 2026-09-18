# VikaTennis V4.19 FINAL

1. Copy `.env.example` to `.env`.
2. Set `TELEGRAM_BOT_TOKEN`.
3. Optional: set `LIVETENNISAPI_KEY` for live matches.
4. Run `python scripts_v418_healthcheck.py`.
5. Run `python start_bot.py`.

Telegram: `/predict`, `/form`, `/h2h`, `/live`, `/errors`, `/status`, `/model`.

A historical live champion is **not claimed as trained** until real point-by-point tapes are supplied. The production fallback remains the tested hand-built live model.
