# VikaTennis v4.7 — production-ready live ML layer

## What is new
V4.7 adds a real historical live XGBoost training pipeline. It does **not** use the external provider's `win_probability_p1` or `danger` as model features.

The live model learns from causal snapshots containing:
- pre-match prior (logit)
- set/game state
- point score
- server
- elapsed time / sequence
- point momentum when `point_winner` is available

Training is split by whole matches in chronological order, so snapshots from one match cannot leak across train/validation/test.

The bot automatically uses `models/vika_live_v47.joblib` when it exists. If it does not exist, it safely falls back to the tested v4.5 live model + 100k remainder Monte Carlo.

## What you need to configure

### Always required
1. Python 3.10+ recommended.
2. Install dependencies:
   `pip install -r requirements_v47.txt`
3. Create `.env` from `.env.example`.
4. Set `TELEGRAM_BOT_TOKEN`.

### Optional but required for real live API
Set `LIVETENNISAPI_KEY`.

The Live Tennis API subscription level determines which historical/live capabilities are available. A historical tape/model-training workflow needs a plan that exposes historical match/tape data; native WebSocket live streaming needs the corresponding WebSocket access.

## Run the bot

`python vikatenis_v3_bot.py`

## Train the real V4.7 live model

### Option A — use JSONL history
Each line must contain one historical HistoryTape envelope, for example:
`{"match_id":"123","tape":{...}}`

Then:
`python scripts_v47_train_live.py --history-jsonl data/live_history.jsonl --output models/vika_live_v47.joblib`

### Option B — fetch directly from Live Tennis API

`python scripts_v47_fetch_history.py MATCH_ID_1 MATCH_ID_2 ... --complete --output data/live_history.jsonl`

Then train:
`python scripts_v47_train_live.py --history-jsonl data/live_history.jsonl`

For a useful model, feed **hundreds/thousands of matches**, not a handful. V4.7 refuses very small datasets.

## Health check

`python scripts_v47_healthcheck.py`

The health check distinguishes:
- bot dependencies/configuration
- optional live API configuration
- presence of the trained V4.7 live model

## Current state of this release

The code and 15-test suite have been verified offline. A real historical V4.7 model is intentionally **not** bundled because no Live Tennis API historical key/data was available during build. The release therefore ships with the safe v4.5 live fallback and a complete reproducible V4.7 trainer.

Do not treat synthetic tests as real-world model accuracy.
