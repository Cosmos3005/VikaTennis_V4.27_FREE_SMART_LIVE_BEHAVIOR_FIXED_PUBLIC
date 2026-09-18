# VikaTennis V4.17 — Walk-Forward Champion

V4.17 adds chronological walk-forward evaluation for the live probability engine.

## What changed
- Three production-style time folds: 2024, 2025, 2026 YTD.
- Whole matches remain atomic across train/test boundaries.
- Each fold trains only on data available before its test period.
- A rolling 120-day validation tail is used for early stopping.
- Each fold reports accuracy, Brier score and log loss for both live XGBoost and the pre-match prior.
- Aggregate champion selection is based on mean log loss, then Brier score.
- No provider `win_probability_p1` or `danger` fields are used as training features.
- The 2026 fold is evaluated only when historical 2026 tapes exist; otherwise it is explicitly skipped.

## Important
The bundled release does not claim real historical walk-forward metrics unless a real point-by-point history JSONL is supplied and the script is run. Synthetic tests are only smoke tests.

## Run
`python scripts_v417_walk_forward.py --history-jsonl data/live_history.jsonl --source livetennis_observed`
