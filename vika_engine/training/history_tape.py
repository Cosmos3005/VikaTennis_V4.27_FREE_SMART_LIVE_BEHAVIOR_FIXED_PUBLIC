from __future__ import annotations
import gzip, json, hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Iterator


def _first(obj: dict, *keys, default=None):
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return default


def _date(obj: dict) -> str:
    v=_first(obj,'date','match_date','played_at','start_time','scheduled_at','event_date',default='')
    return str(v)[:10] if v else ''


def _players(match: dict):
    p1=_first(match,'player1_name','p1_name',default=None)
    p2=_first(match,'player2_name','p2_name',default=None)
    if not p1 or not p2:
        a=_first(match,'player1','p1',default={}) or {}; b=_first(match,'player2','p2',default={}) or {}
        if not isinstance(a,dict): a={'name':a}
        if not isinstance(b,dict): b={'name':b}
        p1=_first(a,'name','player_name',default='P1'); p2=_first(b,'name','player_name',default='P2')
    return str(p1),str(p2)


def _point_winner(row: dict):
    # Prefer explicit point-level fields. A generic `winner` is accepted only when
    # the row clearly looks like a point event, preventing match-winner leakage.
    v=_first(row,'point_winner','pointWinner','winner_point','pointWinnerId',default=None)
    if v is None and any(k in row for k in ('seq','point','point_score','server','serving_player')):
        v=row.get('winner')
    if isinstance(v,dict): v=_first(v,'id','index','player','side','value',default=None)
    if isinstance(v,str):
        z=v.lower().strip()
        if z in ('p1','player1','1','a'): return 1
        if z in ('p2','player2','2','b'): return 2
    try:
        iv=int(float(v))
        if iv in (1,2): return iv
    except Exception: pass
    return None


def normalize_tape(obj: dict, source: str='unknown') -> dict | None:
    if not isinstance(obj,dict): return None
    match=dict(obj.get('match') or {})
    rows=obj.get('tape')
    if rows is None: rows=obj.get('points')
    if rows is None and isinstance(obj.get('data'),dict):
        rows=obj['data'].get('tape') or obj['data'].get('points')
        match={**obj['data'].get('match',{}),**match}
    if not isinstance(rows,list) or not rows: return None
    p1,p2=_players(match)
    winner=_first(match,'winner',default=None)
    if isinstance(winner,dict): winner=_first(winner,'index','side','player','id',default=None)
    try: winner=int(winner) if winner is not None else None
    except Exception: winner=None
    if winner not in (1,2):
        ws=str(_first(match,'winner_name',default='')).strip().lower()
        winner=1 if ws and ws==p1.lower() else 2 if ws and ws==p2.lower() else None
    if winner not in (1,2): return None
    clean=[]
    for i,r in enumerate(rows,1):
        if not isinstance(r,dict): continue
        x=dict(r); pw=_point_winner(x)
        if pw is not None: x['point_winner']=pw
        x['seq']=int(x.get('seq') or i)
        clean.append(x)
    if not clean: return None
    meta=dict(obj.get('meta') or {})
    meta['source']=source
    meta['point_source']=meta.get('point_source') or ('observed_live' if source.startswith('livetennis') else source)
    meta['normalized']=True
    mid=str(_first(match,'id','match_id',default=obj.get('match_id') or ''))
    if not mid:
        raw=f"{_date(match)}|{p1}|{p2}".encode(); mid=hashlib.sha1(raw).hexdigest()[:16]
    match.update({'id':mid,'match_id':mid,'player1_name':p1,'player2_name':p2,'winner':winner,'date':_date(match)})
    return {'match':match,'tape':clean,'meta':meta}


def iter_jsonl(path: str|Path) -> Iterator[dict]:
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try: yield json.loads(line)
                except json.JSONDecodeError: continue


def iter_sources(paths: Iterable[str|Path], source: str='unknown') -> Iterator[dict]:
    seen=set()
    for path in paths:
        for obj in iter_jsonl(path):
            t=normalize_tape(obj,source=source)
            if not t: continue
            mid=t['match']['id']
            if mid in seen: continue
            seen.add(mid); yield t


def write_jsonl(records: Iterable[dict], path: str|Path) -> int:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); n=0
    with path.open('w',encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n'); n+=1
    return n
