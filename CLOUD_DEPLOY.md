# Vika bot on a cloud VPS (Docker)

The bot is a continuously running Telegram polling process. Use a VPS or another
container host that supports always-on workers and outbound HTTPS. A free web
host that sleeps idle is not suitable.

## Required files and credentials

The public Git repository intentionally does not contain private credentials or
model/data artifacts. Before starting the container, provide:

- `.env` with `TELEGRAM_BOT_TOKEN` and `LIVETENNISAPI_KEY`.
- `models/vika_models_v422.joblib` (or one of the older supported model files).
- `models/player_state_v422.json` (or one of the older supported state files).

The model and state files are required by `start_bot.py`; without them the
container exits instead of generating ungrounded predictions. The optional
`THE_ODDS_API_KEY` enables bookmaker-market features. Never put `.env` or model
files in Git.

## Deploy

On an Ubuntu/Debian VPS with Docker Engine and the Compose plugin installed:

```sh
git clone https://github.com/Cosmos3005/VikaTennis_V4.27_FREE_SMART_LIVE_BEHAVIOR_FIXED_PUBLIC.git vika
cd vika
cp .env.example .env
mkdir -p models
# Securely copy the model and player-state artifacts into ./models/
chmod 600 .env
docker compose -f compose.yaml up -d --build
```

Edit `.env` on the server before starting the bot. Keep the Telegram bot token
and API keys out of shell history, chat, and Git. The container mounts models
read-only and keeps its writable runtime data in a Docker volume.

## Verify and operate

```sh
docker compose -f compose.yaml ps
docker compose -f compose.yaml logs --tail=100 -f vika-bot
docker compose -f compose.yaml restart vika-bot
docker compose -f compose.yaml down
```

The first startup checks required model/state files and the Telegram token. In
Telegram, send `/start`, then request `/day`; the report now distinguishes
players missing from the historical state from other prediction errors.

## Data limitation

The Live Tennis API upcoming-fixture endpoint does not supply historical player
results. If a player's profile is absent from the local state, the bot will
identify the missing player but must skip that fixture. Refreshing historical
results requires a Live Tennis API key with History access and the historical
base archive used by the training scripts. An API `403` means that entitlement
is not enabled for that key; a ChatGPT subscription does not grant it.
