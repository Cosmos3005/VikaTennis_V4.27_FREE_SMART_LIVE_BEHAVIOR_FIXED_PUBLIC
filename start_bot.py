from __future__ import annotations
import os, sys
from pathlib import Path
from vika_engine.paths import ROOT
from dotenv import load_dotenv
load_dotenv()
root=ROOT
if not os.getenv('TELEGRAM_BOT_TOKEN'):
    raise SystemExit('TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and add your bot token.')
model_candidates=('models/vika_models_v422.joblib','models/vika_models_v42.joblib','models/vika_models_v4.joblib')
if not any((root/x).exists() for x in model_candidates):
    raise SystemExit('Missing Vika model artifact')
if not any((root/x).exists() for x in ('models/player_state_v422.json','models/player_state_v414.json','models/player_state_v4.json')):
    raise SystemExit('Missing player state model')
from vikatenis_v3_bot import main
main()
