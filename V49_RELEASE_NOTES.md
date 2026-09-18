# VikaTennis v4.9 — Champion Backtest

V4.9 adds the final evaluation layer for the historical live pipeline.

## What it does
- Evaluates the trained V4.7/V4.8 live XGBoost on a supplied holdout tape set.
- Compares the pre-match prior, live XGBoost, and a conservative live-state blend.
- Reports accuracy, Brier score, and log loss.
- Ranks candidates by lowest log loss, then Brier.
- Writes `models/champion_backtest_v49.json`.

## Important
The champion script must be run on a holdout set that was **not used to fit the model**. It does not claim real-world champion metrics until real historical tapes have been downloaded and a chronological holdout has been supplied.

## Historical window
Default V4.8 collection window is 2021-09-08 through 2026-09-08. The Live Tennis API documentation confirms that 2023-present is recorded point-by-point history and 2013-2022 is reconstructed archive tape; reconstructed rows have no real timestamps or vendor model outputs.

## Commands
```bash
python scripts_v48_pipeline.py --train
python scripts_v49_champion.py --history-jsonl data/live_history_v48.jsonl --model models/vika_live_v48.joblib
```
