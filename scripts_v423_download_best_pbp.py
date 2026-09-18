from __future__ import annotations
import argparse, gzip, json, time
from pathlib import Path
from vika_engine.providers.history import LiveTennisHistoryProvider


def main():
    ap=argparse.ArgumentParser(description='Download a quota-safe sample of point-complete tapes')
    ap.add_argument('--start',default='2026-01-01')
    ap.add_argument('--end',default=None)
    ap.add_argument('--tour',choices=['atp','wta'],default=None)
    ap.add_argument('--limit',type=int,default=50,help='maximum tapes to download')
    ap.add_argument('--out',default='data/pbp/history_tapes.jsonl.gz')
    ap.add_argument('--complete',action='store_true')
    a=ap.parse_args(); p=LiveTennisHistoryProvider()
    if not p.available: raise SystemExit('LIVETENNISAPI_KEY is required')
    params={'from':a.start,'limit':min(max(a.limit,1),200),'points_complete':'true'}
    if a.end: params['to']=a.end
    if a.tour: params['tour']=a.tour
    payload=p.history_matches(**params)
    items=payload.get('data',[]) if isinstance(payload,dict) else []
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    seen=set()
    if Path(a.out).exists():
        with gzip.open(a.out,'rt',encoding='utf-8') as f:
            for line in f:
                try: seen.add(str(json.loads(line).get('match_id')))
                except Exception: pass
    count=0
    with gzip.open(a.out,'at',encoding='utf-8') as f:
        for m in items:
            mid=str(m.get('id') or '')
            if not mid or mid in seen: continue
            obj=p.history_tape(mid,complete=a.complete)
            meta=obj.get('meta') or {}
            coverage=str(meta.get('coverage','')).lower()
            source=str(meta.get('point_source','')).lower()
            if source=='game' or coverage in ('none',''):
                continue
            f.write(json.dumps({'match_id':mid,'tape':obj},ensure_ascii=False,separators=(',',':'))+'\n')
            print('saved',mid,coverage,meta.get('basis'))
            count += 1
            if count >= a.limit: break
            time.sleep(.05)
    print(json.dumps({'requested':a.limit,'saved':count,'out':a.out},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
