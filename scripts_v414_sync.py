from __future__ import annotations
import argparse, json, os, time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

BASE='https://api.livetennisapi.com/api/public/v1'


def _date_from_obj(obj: dict[str, Any]) -> date | None:
    for key in ('date','played_at','start_time','scheduled_at','match_date','event_date'):
        v=obj.get(key)
        if not v: continue
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            pass
    return None


def api_get(key: str, path: str, params: dict[str, Any], timeout: int = 60):
    headers={'Authorization': f'Bearer {key}'}
    for attempt in range(4):
        r=requests.get(BASE+path, headers=headers, params=params, timeout=timeout)
        if r.status_code == 429:
            retry=int(r.headers.get('Retry-After','10') or 10)
            time.sleep(min(max(retry,2),120)); continue
        if r.status_code in (401,403):
            raise RuntimeError(f'Live Tennis API {r.status_code}: check LIVETENNISAPI_KEY and history plan')
        r.raise_for_status()
        return r.json()
    raise RuntimeError('Live Tennis API rate limit did not clear after retries')


def extract_items(payload: Any) -> tuple[list[dict], bool]:
    if isinstance(payload,list): return payload, False
    if not isinstance(payload,dict): return [], False
    for key in ('data','matches','items','results'):
        val=payload.get(key)
        if isinstance(val,list):
            meta=payload.get('meta') or {}
            more=bool(meta.get('has_more', payload.get('has_more', False)))
            return val, more
    return [], False


def normalize_match(m: dict[str,Any]) -> dict[str,Any] | None:
    # API has changed envelope names over time; accept the documented winner/loser
    # objects and common flat player fields without inventing missing dates.
    w=m.get('winner') or m.get('player1') or {}
    l=m.get('loser') or m.get('player2') or {}
    if not isinstance(w,dict): w={'name':w}
    if not isinstance(l,dict): l={'name':l}
    wn=w.get('name') or m.get('winner_name') or m.get('player1_name')
    ln=l.get('name') or m.get('loser_name') or m.get('player2_name')
    if not wn or not ln: return None
    d=_date_from_obj(m)
    if d is None: return None
    # Completed match list is results-only, so deliberately do NOT invent serve stats.
    return {
        'tourney_date': d.strftime('%Y%m%d'),
        'date': d.isoformat(),
        'surface': m.get('surface') or 'Hard',
        'winner_id': w.get('id') or w.get('player_id') or '',
        'winner_name': wn,
        'winner_rank': w.get('rank'),
        'loser_id': l.get('id') or l.get('player_id') or '',
        'loser_name': ln,
        'loser_rank': l.get('rank'),
        'score': m.get('score') or '',
        'minutes': m.get('minutes'),
        'tour': str(m.get('tour') or '').lower(),
        'draw': str(m.get('draw') or 'singles').lower(),
        'match_num': m.get('id') or m.get('match_id') or 0,
        'source': 'livetennisapi_history_results',
    }


def sync(start: date, end: date, out: Path, tour: str | None = None, max_pages: int = 1000) -> dict:
    key=os.getenv('LIVETENNISAPI_KEY')
    if not key: raise SystemExit('LIVETENNISAPI_KEY is required for 2023+ history sync')
    out.parent.mkdir(parents=True,exist_ok=True)
    existing=[]
    if out.exists():
        existing=json.loads(out.read_text(encoding='utf-8'))
    by_id={str(x.get('match_num')):x for x in existing if x.get('match_num')}
    by_sig={(x.get('date'),x.get('winner_name'),x.get('loser_name')):x for x in existing}
    offset=0; pages=0; fetched=0; added=0
    while pages < max_pages:
        params={'from':start.isoformat(),'to':end.isoformat(),'limit':200,'offset':offset}
        if tour: params['tour']=tour
        payload=api_get(key,'/history/matches',params)
        items,has_more=extract_items(payload)
        if not items: break
        pages += 1; fetched += len(items)
        for raw in items:
            n=normalize_match(raw)
            if not n: continue
            if not (start <= date.fromisoformat(n['date']) <= end): continue
            if n['draw'] not in ('singles',''): continue
            key_id=str(n.get('match_num') or '')
            sig=(n['date'],n['winner_name'],n['loser_name'])
            if key_id and key_id in by_id: by_id[key_id].update(n)
            elif sig in by_sig: by_sig[sig].update(n)
            else:
                existing.append(n); added+=1
                if key_id: by_id[key_id]=n
                by_sig[sig]=n
        offset += len(items)
        if not has_more and len(items) < 200: break
        if len(items) == 0: break
    existing.sort(key=lambda x:(x.get('date',''), str(x.get('match_num',''))))
    out.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'start':str(start),'end':str(end),'pages':pages,'fetched':fetched,'added':added,'total_cached':len(existing),'out':str(out)}


def main():
    load_dotenv()
    ap=argparse.ArgumentParser(description='VikaTennis V4.14: sync completed 2023+ results into local player-state cache')
    ap.add_argument('--start',default='2026-01-01')
    ap.add_argument('--end',default=str(date.today()))
    ap.add_argument('--out',default='data/live_results_v414.json')
    ap.add_argument('--tour',choices=['atp','wta'])
    ap.add_argument('--rebuild-state',action='store_true')
    a=ap.parse_args()
    result=sync(date.fromisoformat(a.start),date.fromisoformat(a.end),Path(a.out),a.tour)
    if a.rebuild_state:
        print('[INFO] --rebuild-state uses the full local archive plus synced results.')
        # We intentionally leave service stats from the local archive untouched for synced
        # rows: the listing endpoint is results-only. Ratings/form/H2H can still be updated.
        from vika_engine.ratings.player_state import PlayerStateStore
        base=Path('data/all_matches_2015_2025.csv.gz')
        if not base.exists(): raise SystemExit(f'Missing {base}')
        df=pd.read_csv(base,low_memory=False)
        extra=pd.DataFrame(json.loads(Path(a.out).read_text(encoding='utf-8')))
        if len(extra):
            for c in df.columns:
                if c not in extra.columns: extra[c]=None
            extra=extra[[c for c in df.columns]]
            df=pd.concat([df,extra],ignore_index=True)
        store=PlayerStateStore(); store.ingest(df)
        store.save('models/player_state_v414.json')
        result['state']='models/player_state_v414.json'; result['state_max_date']=str(store.max_date)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
