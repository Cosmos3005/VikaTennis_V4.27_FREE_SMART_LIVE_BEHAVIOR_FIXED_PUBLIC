from __future__ import annotations
import re
from typing import Any
import numpy as np


def _f(v, default=None):
    try: return float(v)
    except Exception: return default


def parse_score(score: Any):
    raw = str((score or {}).get('display') if isinstance(score,dict) else score or '')
    if isinstance(score,dict): raw = score.get('display') or score.get('text') or score.get('score') or ''
    return [(int(a),int(b)) for a,b in re.findall(r'(\d+)\s*[-:]\s*(\d+)', str(raw))]


def _live_distribution(p1p: float, best_of: int, n: int = 15000):
    """Approximate remainder distribution from live match probability.

    We use the same MatchSimulator family as the core engine, but only as a
    distribution generator. The official/live probability remains the primary
    winner estimator; this is for totals/handicap candidate probabilities.
    """
    pgame=min(.70,max(.30,.5+(p1p-.5)*.22))
    need=2 if best_of==3 else 3
    rng=np.random.default_rng(20260910)
    totals=[];diffs=[];sets=[]
    for _ in range(n):
        s1=s2=tg=gd=0;ns=0
        while s1<need and s2<need:
            a=b=0
            while True:
                if rng.random()<pgame:a+=1
                else:b+=1
                if (a>=6 or b>=6) and abs(a-b)>=2:break
                if a==6 and b==6:
                    # simple tiebreak approximation
                    if rng.random() < pgame: a += 1
                    else: b += 1
                    if a==6 and b==6: break
                    break
            tg += a+b; gd += a-b; ns += 1
            if a>b:s1+=1
            else:s2+=1
        totals.append(tg);diffs.append(gd);sets.append(ns)
    return np.asarray(totals),np.asarray(diffs),np.asarray(sets)


def market_candidates(p1: str, p2: str, live: dict, pre: dict, frame: dict):
    """Generate calibrated-ish live candidates across several tennis markets.

    No bookmaker price is invented here. Each candidate is useful only after
    joining it to a real live odds quote from an odds provider.
    """
    p1p=max(.001,min(.999,float(live.get('p1_win',pre.get('p1_win',.5)))))
    p2p=1-p1p; conf=float(live.get('confidence',0)); sets=parse_score(frame.get('score') or frame.get('current_score') or '')
    g1=sum(a for a,b in sets); g2=sum(b for a,b in sets); current_total=g1+g2
    best_of=int(pre.get('best_of',3) or 3); out=[]
    def add(kind,label,prob,line=None,side=None,c=0,reason=''):
        prob=max(.001,min(.999,float(prob)))
        out.append({'market':kind,'label':label,'prob':prob,'fair_odds':1/prob,'line':line,'side':side,'confidence':float(c),'reason':reason})

    # 1) Match winner
    if max(p1p,p2p)>=.62:
        side=p1 if p1p>=p2p else p2; add('match_winner',f'Победа {side}',max(p1p,p2p),side=side,c=conf,reason='LIVE win probability')

    # For games/set markets, simulate the remainder and add the already-played score.
    if sets:
        rt,rd,rs=_live_distribution(p1p,best_of,n=8000)
        total_dist=current_total+rt; diff_dist=(g1-g2)+rd
        for line in np.arange(max(17.5,current_total+2.5),min(45.5,current_total+18.5),1.0):
            prob=float(np.mean(total_dist>line))
            if .60<=prob<=.80:
                side='ТБ' if prob>=.5 else 'ТМ'; p=prob if side=='ТБ' else 1-prob
                add('total_games',f'{side} {line:.1f} геймов',p,line,side,conf*.82,'LIVE-счёт + симуляция оставшейся части')
        for line in np.arange(-8.5,9.0,1.0):
            prob=float(np.mean(diff_dist+line>0))
            if .20<=prob<=.80:
                if prob >= .5:
                    side=p1; market_line=line; p=prob
                else:
                    side=p2; market_line=-line; p=1-prob
                if .60<=p<=.80:
                    add('game_handicap',f'Фора {side} {market_line:+.1f}',p,market_line,side,conf*.86,'LIVE-счёт + симуляция разницы геймов')
        # Set winner: use match probability as a conservative proxy only late in a set.
        last1,last2=sets[-1]
        if abs(last1-last2)<=1 or last1>=4 or last2>=4:
            side=p1 if p1p>=p2p else p2
            prob=max(.55,min(.88,.5+(max(p1p,p2p)-.5)*.85))
            add('current_set_winner',f'Победа в текущем сете: {side}',prob,side=side,c=conf*.88,reason='текущий счёт сета + LIVE модель')
        # Total sets directly from the remainder simulation is not a full match-set
        # probability, so only expose it as a watch candidate, not an auto bet.
        if best_of==3 and len(sets)<=2:
            p3=float(np.mean(rs>=3))
            if p3>=.58:
                add('total_sets','ТБ 2.5 сета',p3,2.5,'ТБ',conf*.70,'LIVE remainder simulation')

    # Deduplicate same market/line/side and keep strongest probability/quality.
    uniq={}
    for x in out:
        k=(x['market'],x.get('line'),x.get('side'))
        if k not in uniq or x['prob']*x['confidence']>uniq[k]['prob']*uniq[k]['confidence']:uniq[k]=x
    return sorted(uniq.values(),key=lambda x:(x['prob']-.5)*x['confidence'],reverse=True)
