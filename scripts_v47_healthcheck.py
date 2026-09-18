from __future__ import annotations
import importlib.util, os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
checks=[]
for mod in ['pandas','numpy','sklearn','xgboost','joblib','dotenv','telegram','requests','websocket','livetennisapi']:
    checks.append((f'python:{mod}', bool(importlib.util.find_spec(mod))))
checks += [
    ('model:v4.2', (ROOT/'models/vika_models_v42.joblib').exists()),
    ('state:player_state', (ROOT/'models/player_state_v4.json').exists()),
    ('model:live_v4.7', (ROOT/'models/vika_live_v47.joblib').exists()),
    ('env:TELEGRAM_BOT_TOKEN', bool(os.getenv('TELEGRAM_BOT_TOKEN'))),
    ('env:LIVETENNISAPI_KEY', bool(os.getenv('LIVETENNISAPI_KEY'))),
]
for k,v in checks: print(('OK  ' if v else 'MISS'), k)
print('\nBOT READY' if all(v for k,v in checks if not k.startswith('model:live_v4.7') and not k.startswith('env:LIVETENNISAPI_KEY')) else '\nBOT NOT READY')
print('Live ML: READY' if dict(checks).get('model:live_v4.7') else 'Live ML: fallback v4.5 until a real historical model is trained')
