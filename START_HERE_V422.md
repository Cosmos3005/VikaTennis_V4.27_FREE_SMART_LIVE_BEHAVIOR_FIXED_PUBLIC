# VikaTennis V4.22 — Data Refresh + Walk-Forward

## 1. Configure API
Copy `.env.example` to `.env` and set `LIVETENNISAPI_KEY`.

For the production live bot, ULTRA is required for WebSocket and live point events. Historical tapes require a History/BASIC entitlement; monthly bulk tape packages require PRO/History Pro or higher.

## 2. Refresh 2026 results
```bash
python scripts_v422_refresh.py --start 2026-01-01 --end 2026-09-09
```

Optionally limit to one tour:
```bash
python scripts_v422_refresh.py --tour atp
python scripts_v422_refresh.py --tour wta
```

## 3. Rebuild Player State
The default mode is incremental and uses the existing V4.14 state as the baseline, so it does not spend hours replaying the entire 2015–2025 archive.

```bash
python scripts_v422_rebuild_state.py
```

Full rebuild:
```bash
python scripts_v422_rebuild_state.py --full
```

## 4. Train
```bash
python scripts_v422_train.py
```

The split is chronological: 70% train / 15% validation / 15% holdout test. No random shuffle.

## 5. Point tapes
For selected matches:
```bash
python scripts_v422_tape_download.py --match-ids 123,456,789 --complete
```

The downloader refuses to promote `game`/`none` coverage to point data.

## 6. Audit and launch
```bash
python scripts_v420_production_audit.py
pytest -q
python start_bot.py
```

### Important
The bot must never claim current form from stale 2025 state. After the refresh, the state report must show a current 2026 max date.
