from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    load_dotenv(); root=Path(__file__).resolve().parent; checks=[]
    def ck(name,ok,detail=''):
        checks.append((name,bool(ok))); print(('OK  ' if ok else 'MISS'),name,detail)
    for mod in ['pandas','numpy','sklearn','xgboost','joblib','telegram','dotenv','requests']:
        try: __import__(mod); ck('python:'+mod,True)
        except Exception as e: ck('python:'+mod,False,str(e))
    ck('model:v4.2',(root/'models/vika_models_v42.joblib').exists())
    ck('state:bundled',(root/'models/player_state_v4.json').exists())
    ck('archive:2015-2025',(root/'data/all_matches_2015_2025.csv.gz').exists())
    ck('sync:v4.14',(root/'scripts_v414_sync.py').exists())
    ck('env:TELEGRAM_BOT_TOKEN',bool(os.getenv('TELEGRAM_BOT_TOKEN')),'required to run Telegram')
    ck('env:LIVETENNISAPI_KEY',bool(os.getenv('LIVETENNISAPI_KEY')),'required for automatic 2026 sync; optional for offline bot')
    bad=[n for n,ok in checks if not ok and n!='env:LIVETENNISAPI_KEY']
    print('\nREADY' if not bad and os.getenv('TELEGRAM_BOT_TOKEN') else '\nSETUP NEEDED')
    return 0 if not bad else 1
if __name__=='__main__': raise SystemExit(main())
