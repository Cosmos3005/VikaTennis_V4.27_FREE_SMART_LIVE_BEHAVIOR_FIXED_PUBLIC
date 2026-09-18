# VikaTennis V4.24 — Production Refresh

## One-time setup
Create `.env` from `.env.example` and put the private `LIVETENNISAPI_KEY` there. Never put the key in chat or source control.

## One-button refresh
Run `run_vika.bat` on Windows.

The pipeline:
1. downloads current 2026 completed singles results;
2. qualifies matches with point-level tape coverage;
3. downloads a capped PBP sample (default 300 matches);
4. extracts honest point/server/return statistics without inventing points;
5. updates Player State incrementally;
6. trains the chronological model;
7. runs the complete regression suite;
8. writes `models/v424_production_report.json`.

Before replacing key artifacts it creates `.bak` copies. A failed refresh does not delete the previous artifacts.

## Important
PBP is treated as a separate evidence layer. A match with game-level or incomplete coverage is never promoted to point-level training data. Live Tennis API documentation says the 2023→now tape is not guaranteed complete and consumers must check coverage/point source before backtesting.
