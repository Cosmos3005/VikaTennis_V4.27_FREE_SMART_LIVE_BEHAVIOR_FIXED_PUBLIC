# VikaTennis v4.10 — Walk-Forward Live Champion

Expanding-window, time-ordered live backtest. Default folds:
- train through 2023-12-31 -> test 2024
- train through 2024-12-31 -> test 2025
- train through 2025-12-31 -> test 2026-01-01..2026-09-08

Each fold reserves the final 120 training days for chronological validation and keeps whole matches atomic across splits.

Run:
`python scripts_v410_walk_forward.py --history-jsonl data/live_history_v48.jsonl --output models/walk_forward_v410.json`

No real historical metrics are claimed until real tapes are supplied.
