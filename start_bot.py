from __future__ import annotations
import os, sys
from pathlib import Path
from vika_engine.paths import ROOT
from dotenv import load_dotenv
load_dotenv()
root=ROOT
if not os.getenv('TELEGRAM_BOT_TOKEN'):
    raise SystemExit('TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and add your bot token.')
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure models directory exists
(root / 'models').mkdir(exist_ok=True)

model_candidates = ('models/vika_models_v422.joblib', 'models/vika_models_v42.joblib', 'models/vika_models_v4.joblib')
model_file = next((x for x in model_candidates if (root/x).exists()), None)
if model_file:
    logger.info(f"Loaded model from {model_file}")
else:
    logger.warning("No model file found - bot will run with default behavior. Upload models to /app/models/")

state_candidates = ('models/player_state_v422.json', 'models/player_state_v414.json', 'models/player_state_v4.json')
state_file = next((x for x in state_candidates if (root/x).exists()), None)
if state_file:
    logger.info(f"Loaded state from {state_file}")
else:
    logger.warning("No player state file found - initializing empty state. Upload state to /app/models/")
from vikatenis_v3_bot import main
main()
