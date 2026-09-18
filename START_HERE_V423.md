# Vika Tennis V4.23 — automatic data refresh

V4.23 keeps the V4.22 leakage-safe pipeline and adds a one-command updater.

## What it does

1. Downloads completed singles results from the official Live Tennis API for 2026.
2. Updates the leakage-safe Player State incrementally.
3. Retrains the chronological model (70/15/15 train/validation/test).
4. Runs the core V4.21/V4.22 regression tests.

The API history endpoint covers completed matches from January 2023 to now; PBP tape is available per match on plans that include History. Check coverage before treating PBP as complete. See the official docs: https://docs.livetennisapi.com/

## One-time setup

### Windows

```powershell
copy .env.example .env
notepad .env
```

Put your private `LIVETENNISAPI_KEY` into `.env`.

Install dependencies:

```powershell
py -m pip install -r requirements_v47.txt
```

Then run:

```powershell
py scripts_v423_auto_update.py
```

The updater writes:

- `data/live_results_2023_now.csv.gz`
- `models/player_state_v422.json`
- `models/vika_models_v422.joblib`
- `models/v422_training_report.json`
- `models/v423_refresh_report.json`

## Important

Do not use random train/test splits. Do not train on live current score as a completed target. Retired/walkover/default/abandoned matches are excluded by the existing target validation.

## PBP

Do NOT blindly download every tape one-by-one. Coverage and API quota must be checked first. Use the existing tape downloader for selected matches, or monthly bulk history packages when the account tier provides them.
