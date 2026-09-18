from __future__ import annotations
import argparse,json
from vika_engine.providers.history import LiveTennisHistoryProvider

ap=argparse.ArgumentParser(description='Fetch Live Tennis API historical tapes to JSONL')
ap.add_argument('match_ids',nargs='+')
ap.add_argument('--output',default='data/live_history.jsonl')
ap.add_argument('--complete',action='store_true')
a=ap.parse_args(); p=LiveTennisHistoryProvider()
if not p.available: raise SystemExit('LIVETENNISAPI_KEY is required')
with open(a.output,'w',encoding='utf-8') as f:
    for mid in a.match_ids:
        tape=p.history_tape(mid,complete=a.complete)
        f.write(json.dumps({'match_id':mid,'tape':tape},ensure_ascii=False)+'\n')
        print('saved',mid)
print(a.output)
