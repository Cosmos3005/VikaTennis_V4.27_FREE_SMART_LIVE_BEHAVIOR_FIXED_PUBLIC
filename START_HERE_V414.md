# VikaTennis v4.14 — start here

## Goal
V4.14 is the first production-oriented sync layer. It keeps the 2015–2025 local archive and can pull completed 2023+ results from Live Tennis API so the player state can be refreshed for the current season.

## Install

```bash
pip install -r requirements_v47.txt
```

Copy `.env.example` to `.env` and set:

```text
TELEGRAM_BOT_TOKEN=...
LIVETENNISAPI_KEY=...
```

## Health check

```bash
python scripts_v414_healthcheck.py
```

## Sync 2026

```bash
python scripts_v414_sync.py --start 2026-01-01 --end 2026-09-08 --rebuild-state
```

The API completed-match listing is results-oriented. The sync therefore updates ratings/form/H2H chronology but does **not** invent service statistics for new rows. The existing 2015–2025 service/return history remains intact.

## Run bot

```bash
python start_bot.py
```

## Important

The Live Tennis API's `/history/matches` endpoint covers completed matches from January 2023 onward. BASIC provides per-match tapes; PRO adds monthly bulk packages; ULTRA adds the reconstructed 2013–2022 tapes and live point stream. Coverage must be checked per match before live backtesting.
