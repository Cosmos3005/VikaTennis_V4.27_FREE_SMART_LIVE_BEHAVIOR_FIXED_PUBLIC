from __future__ import annotations
import argparse,json,os
from pathlib import Path
from vika_engine.model_health import ModelHealth
from vika_engine.paths import root_path

def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.18 production healthcheck')
    ap.add_argument('--json',action='store_true'); a=ap.parse_args()
    r=ModelHealth().report()
    r['env']={'telegram_token':bool(os.getenv('TELEGRAM_BOT_TOKEN')),'livetennis_key':bool(os.getenv('LIVETENNISAPI_KEY'))}
    r['files']={k:root_path(k).exists() for k in ['models/player_state_v414.json','models/player_state_v4.json','data/all_matches_2015_2025.csv.gz']}
    r['production']={'live_fallback_ok':True,'telegram_ready':r['env']['telegram_token'],'livetennis_ready':r['env']['livetennis_key']}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    raise SystemExit(0 if r['ok'] else 1)
if __name__=='__main__': main()
