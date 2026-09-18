from __future__ import annotations
import os, sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    checks=[]
    def ck(name, ok, detail=''):
        checks.append((name, bool(ok), detail)); print(('OK  ' if ok else 'MISS'), name, detail)
    for mod in ['pandas','numpy','sklearn','xgboost','joblib','telegram','dotenv','requests']:
        try: __import__(mod); ck('python:'+mod, True)
        except Exception as e: ck('python:'+mod, False, str(e))
    ck('model:v4.2', (root/'models/vika_models_v42.joblib').exists(), 'models/vika_models_v42.joblib')
    ck('state:through_2025', (root/'models/player_state_v4.json').exists(), '2025-12-29 snapshot bundled')
    ck('archive:2015-2025', (root/'data/all_matches_2015_2025.csv.gz').exists(), '605k+ matches source')
    token=bool(os.getenv('TELEGRAM_BOT_TOKEN')); key=bool(os.getenv('LIVETENNISAPI_KEY'))
    ck('env:TELEGRAM_BOT_TOKEN',token,'required to start Telegram bot')
    ck('env:LIVETENNISAPI_KEY',key,'optional; enables live/history API')
    bad=[x for x in checks if not x[1] and not x[0].startswith('env:LIVETENNISAPI_KEY')]
    print('\nREADY' if not bad and token else '\nSETUP NEEDED')
    return 0 if not bad else 1
if __name__=='__main__': raise SystemExit(main())
