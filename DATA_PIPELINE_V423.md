# V4.23 data pipeline

**Primary production source:** official Live Tennis API.

- Results: `GET /history/matches` — completed matches, January 2023 → now.
- Tape: `GET /history/matches/{matchId}` — point-by-point history where coverage exists.
- Coverage: `GET /history/coverage` — measure completeness before backtesting.
- PRO: monthly bulk history packages are available when the account tier unlocks them.

The project deliberately does not fabricate missing points. Game-level or reconstructed data must be labelled and never mixed with live point data as if they were identical.

## Recommended data strategy

1. Use the existing 2015–2025 archive for broad training.
2. Pull 2026 completed results with `scripts_v423_auto_update.py`.
3. Update Player State incrementally.
4. Retrain chronologically.
5. Pull point-complete tapes with `scripts_v423_download_best_pbp.py` for PBP feature development/backtesting.
6. For large PBP history, prefer the official monthly bulk packages instead of thousands of individual requests when the subscription permits.
