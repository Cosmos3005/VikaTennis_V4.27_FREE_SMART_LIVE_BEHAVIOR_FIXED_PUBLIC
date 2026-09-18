from __future__ import annotations
import argparse, gzip, json, time
from pathlib import Path
from vika_engine.providers.history import LiveTennisHistoryProvider


def main():
    ap=argparse.ArgumentParser(description='V4.22 point tape downloader with honest coverage')
    ap.add_argument('--match-ids',required=True,help='comma-separated match ids')
    ap.add_argument('--out',default='data/pbp/history_tapes.jsonl.gz')
    ap.add_argument('--complete',action='store_true')
    a=ap.parse_args(); p=LiveTennisHistoryProvider()
    if not p.available: raise SystemExit('LIVETENNISAPI_KEY is required')
    ids=[x.strip() for x in a.match_ids.split(',') if x.strip()]
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    mode='at' if Path(a.out).exists() else 'wt'
    seen=set()
    if Path(a.out).exists():
        with gzip.open(a.out,'rt',encoding='utf-8') as f:
            for line in f:
                try: seen.add(str(json.loads(line).get('match_id')))
                except Exception: pass
    with gzip.open(a.out,mode,encoding='utf-8') as f:
        for mid in ids:
            if mid in seen: continue
            obj=p.history_tape(mid,complete=a.complete)
            meta=obj.get('meta') or {}
            # Never promote game-level coverage to point-level.
            if str(meta.get('point_source','')).lower()=='game' or str(meta.get('coverage','')).lower()=='none':
                continue
            f.write(json.dumps({'match_id':mid,'tape':obj},ensure_ascii=False,separators=(',',':'))+'\n')
            print('saved',mid,meta.get('coverage'),meta.get('basis'))
            time.sleep(.03)
    print(a.out)

if __name__=='__main__': main()
