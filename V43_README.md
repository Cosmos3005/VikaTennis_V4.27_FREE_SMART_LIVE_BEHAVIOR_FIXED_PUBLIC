# VikaTennis v4.3 — Live Intelligence

V4.3 adds a real live probability layer on top of the leakage-safe V4.2 pre-match model.

## What changed

- Pre-match probability remains the prior.
- Live score changes move the probability in log-odds space.
- Live service/return, break-point, ace and double-fault signals are incorporated when available.
- Live Tennis API's `win_probability_p1` can be blended as an external signal.
- Optional ULTRA WebSocket client with reconnect-safe token acquisition.
- `/live` lists matches.
- `/live MATCH_ID` computes a live update.
- `/errors` shows settled prediction accuracy/Brier.
- Prediction journal now supports aggregate error reporting.

## API requirements

Live score REST access can run without the WebSocket. Production streaming requires the API tier that exposes `/ws`; the official reference documents `match:<id>` subscriptions, heartbeats and point/signal channels.

## Run

```bash
pip install -r requirements_v43.txt
python vikatenis_v3_bot.py
```

`.env`:

```env
TELEGRAM_BOT_TOKEN=...
LIVETENNISAPI_KEY=...
```

Do not commit secrets. Rotate any token that was previously hard-coded in an old local copy.

## Important model limitation

V4.3 is deliberately conservative: it does not pretend that a single break equals a magical "momentum" number. The pre-match model remains the prior and live evidence is accumulated gradually. The next stage is a point-level state model trained on timestamped point events, not a hand-written heuristic.
