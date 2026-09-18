from __future__ import annotations
import asyncio, logging, re
from typing import Any

log=logging.getLogger('vika.auto')


def _name(m, side):
    p=getattr(m, side, None)
    return getattr(p,'name',None) if p is not None else None

def _id(m): return str(getattr(m,'id',''))

def _frame(m):
    if hasattr(m,'model_dump'):
        try: return m.model_dump()
        except Exception: pass
    return getattr(m,'__dict__',{}) or {}

def _num(v):
    try: return float(v)
    except Exception: return None

def extract_odds(frame: dict[str,Any]):
    """Best-effort odds extraction from common API shapes. Returns moneyline only."""
    candidates=[]
    for key in ('odds','markets','betting','bookmakers','inplay_odds','live_odds'):
        v=frame.get(key)
        if v is not None: candidates.append(v)
    def walk(x):
        if isinstance(x,dict):
            # direct p1/p2 names
            p1=next((x.get(k) for k in ('p1','player1','home','odds1','price1','p1_odds') if x.get(k) is not None),None)
            p2=next((x.get(k) for k in ('p2','player2','away','odds2','price2','p2_odds') if x.get(k) is not None),None)
            a,b=_num(p1),_num(p2)
            if a and b and 1.01<=a<=100 and 1.01<=b<=100: return a,b
            for v in x.values():
                r=walk(v)
                if r:return r
        elif isinstance(x,list):
            for v in x:
                r=walk(v)
                if r:return r
        return None
    for c in candidates:
        r=walk(c)
        if r:return r
    return None

def signal_from_live(p1,p2,live,pre,odds=None):
    p1p=float(live.get('p1_win',.5)); p2p=1-p1p
    conf=float(live.get('confidence',0))
    # Conservative auto-signal threshold: strong model edge + enough live evidence.
    side=1 if p1p>=p2p else 2; prob=max(p1p,p2p)
    if prob < .72 or conf < .55: return None
    selected=p1 if side==1 else p2
    if odds:
        o=odds[0] if side==1 else odds[1]
        fair=1/prob
        edge=prob*o-1
        if o < fair*1.02 or edge < .05: return None
        price=f'{o:.2f}'
        reason=f'LIVE {prob*100:.1f}% при кэфе {price}; fair {fair:.2f}; edge {edge*100:+.1f}%'
    else:
        fair=1/prob; price=f'>= {fair*1.03:.2f}'
        reason=f'LIVE {prob*100:.1f}%; вход только если коэффициент не ниже {price}'
    return {'side':selected,'prob':prob,'odds':odds,'fair':fair,'reason':reason,'confidence':conf}
