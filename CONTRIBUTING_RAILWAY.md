# Vika contributor and Railway handoff

This repository deploys the Telegram bot from the `master` branch to Railway. Keep routine development reviewable and keep production credentials and model files out of Git.

## Development workflow

1. Clone the repository and create a task branch from `master`.
2. Make one focused change. Run the relevant tests and a local startup check when the required model artifacts are available.
3. Open a pull request against `master`; describe the user-visible change, test results, and any new Railway variables.
4. Review the diff and have the project owner approve the production change. Merging to `master` starts the Railway deployment.
5. Check the Railway deployment logs and Telegram smoke test after the deploy.

Do not push directly to `master`. Do not put Telegram tokens, API keys, account credentials, user data, or trained model artifacts in commits, issues, screenshots, or pull request logs. Set secrets in Railway Variables.

## Model files required by production

The Git repository intentionally excludes model files. `start_bot.py` currently requires both:

- One model: `models/vika_models_v422.joblib`, `models/vika_models_v42.joblib`, or `models/vika_models_v4.joblib`
- One player-state file: `models/player_state_v422.json`, `models/player_state_v414.json`, or `models/player_state_v4.json`

The production Railway volume is mounted at `/app/models`. Upload each file to the root of the `vika-models` volume (the volume-root destination maps to the corresponding file under `/app/models`). From PowerShell, after installing and linking the Railway CLI to the Vika project:

```powershell
railway volume files --volume vika-models upload "C:\path\to\vika_models_v42.joblib" /vika_models_v42.joblib
railway volume files --volume vika-models upload "C:\path\to\player_state_v4.json" /player_state_v4.json
railway volume files --volume vika-models list /
```

Use the exact local paths and filenames available to the project owner. Confirm both files appear in the volume before restarting the service. Never upload model files to a Git branch or expose them through a public artifact URL.

## Railway configuration and secrets

Keep Railway production variables in Railway, not in `.env`, the repository, or a PR. Current code reads `TELEGRAM_BOT_TOKEN` and `LIVETENNISAPI_KEY`; a Live Tennis API market reference is available only on PRO and above and covers match winner only. The reference is an implied probability, not a bookmaker decimal price. Check the variable names in code before changing production configuration.

A Railway deployment is not ready just because the image built. Confirm all of the following:

- The latest deployment reports `SUCCESS` and the process stays running.
- Telegram responds to `/start`, `/status`, `/day`, and `/live`.
- Live notifications only use a real quote that matches the same event and market.
- Missing data or prices produce a clear “no signal” response rather than an invented price.
- A restart does not silently lose intended subscribers or auto-monitor settings; persistence is a follow-up item if those settings remain in memory.

## Prediction product acceptance

- Separate pre-match picks from live signals and show the event, market, quoted odds source, timestamp, model probability, and key reason.
- “Pick of the day” means the strongest qualified candidate found by the model, not a guarantee. If nothing passes the filters, say there is no pick.
- Never manufacture a price or combine legs solely to reach a target combined odds.
- A +1.5 set handicap needs a genuine set-handicap quote from a connected odds source. Live Tennis API does not publish set or game handicaps; its market feed is match-winner only. Do not label a match-winner market probability or a game spread as a set-handicap quote.
- Track settled outcomes and calibration by market before describing a market as reliable.

## First deployment recovery

If startup reports `Missing Vika model artifact` or `Missing player state model`, verify the mounted volume contents and filenames first. Do not add large or private artifacts to Git to bypass the volume. If Railway shows an unreviewed staged configuration change, inspect the exact diff and volume IDs before applying it; a staged change is not a successful deployment.
