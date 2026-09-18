from __future__ import annotations
from dataclasses import dataclass, field, asdict
from collections import deque
from datetime import datetime
import math, json, re
from pathlib import Path
import pandas as pd
from .glicko2 import Glicko2Rating

@dataclass
class PlayerState:
    name: str
    player_id: str = ""
    elo: float = 1500.0
    glicko: dict = field(default_factory=lambda: {"rating":1500.0,"rd":350.0,"volatility":0.06})
    surface_glicko: dict = field(default_factory=dict)
    surface_elo: dict = field(default_factory=lambda: {"Hard":1500.0,"Clay":1500.0,"Grass":1500.0,"Carpet":1500.0})
    wins: int = 0
    losses: int = 0
    surface_wins: dict = field(default_factory=dict)
    surface_losses: dict = field(default_factory=dict)
    recent: deque = field(default_factory=lambda: deque(maxlen=50))
    h2h: dict = field(default_factory=dict)
    last_match: str | None = None
    minutes_7d: float = 0.0
    minutes_30d: float = 0.0
    matches_7d: int = 0
    matches_30d: int = 0
    sets_30d: int = 0
    service_points: int = 0
    service_points_won: int = 0
    return_points: int = 0
    return_points_won: int = 0
    opp_elos: deque = field(default_factory=lambda: deque(maxlen=50))

    def form(self, n=10, surface=None, today=None):
        items = list(self.recent)[-n:]
        if surface:
            items = [x for x in items if x.get("surface") == surface][-n:]
        if not items: return 0.5
        vals=[]; weights=[]
        now = pd.Timestamp(today) if today is not None else pd.Timestamp.utcnow()
        for x in items:
            days=max(0,(now-pd.Timestamp(x["date"])).days)
            w=math.exp(-days/30.0)
            vals.append(float(x["win"])); weights.append(w)
        return float(sum(v*w for v,w in zip(vals,weights))/sum(weights)) if weights else .5

    def service_rate(self):
        return self.service_points_won/self.service_points if self.service_points else .62
    def return_rate(self):
        return self.return_points_won/self.return_points if self.return_points else .38
    def opponent_quality(self):
        return sum(self.opp_elos)/len(self.opp_elos) if self.opp_elos else 1500.0

    def to_dict(self):
        d=asdict(self); d["recent"]=list(self.recent); d["opp_elos"]=list(self.opp_elos); return d

class PlayerStateStore:
    """Chronological, leakage-safe player state builder from Sackmann-style match rows."""
    def __init__(self): self.players={}; self.max_date=None; self.aliases={}
    def _p(self, name, pid=""):
        key=str(name).strip().lower()
        if key not in self.players: self.players[key]=PlayerState(str(name).strip(), str(pid or ""))
        if pid and not self.players[key].player_id: self.players[key].player_id=str(pid)
        self.aliases[key]=str(name).strip()
        return self.players[key]
    @staticmethod
    def _date(v):
        try:
            s=str(v).split('.')[0]
            if len(s)==8 and s.isdigit(): return pd.to_datetime(s, format='%Y%m%d')
            return pd.to_datetime(v)
        except: return pd.Timestamp('1970-01-01')
    @staticmethod
    def _score_sets(score):
        out=[]
        for token in str(score or '').split():
            token=re.sub(r'\([^)]*\)','',token)
            if '-' not in token: continue
            try:
                a,b=token.split('-')[:2]; out.append((int(a),int(b)))
            except: pass
        return out
    def ingest(self, df, through=None):
        if df is None or len(df)==0: return
        df=df.copy(); df['match_date']=df['tourney_date'].map(self._date); df=df.sort_values(['match_date','match_num'] if 'match_num' in df else ['match_date'])
        if through is not None: df=df[df['match_date']<=pd.Timestamp(through)]
        for r in df.itertuples(index=False): self._update_row(r)
        if len(df): self.max_date=df['match_date'].max()
    def _get(self,r,k,default=None): return getattr(r,k,default)
    def _update_row(self,r):
        d=self._get(r,'match_date');
        if d is None or pd.isna(d): return
        surf=self._get(r,'surface','Hard') or 'Hard'
        wname=self._get(r,'winner_name',''); lname=self._get(r,'loser_name','')
        if not wname or not lname: return
        wid=self._get(r,'winner_id',''); lid=self._get(r,'loser_id','')
        w=self._p(wname,wid); l=self._p(lname,lid)
        # Ratings before the match are used as opponent quality, then updated.
        w_elo_before=w.elo; l_elo_before=l.elo
        expected=1/(1+10**((l.elo-w.elo)/400)); k=24
        w.elo += k*(1-expected); l.elo += k*(0-(1-expected))
        # Glicko-2 is kept alongside Elo; it provides uncertainty-aware strength.
        wg0=Glicko2Rating(**w.glicko); lg0=Glicko2Rating(**l.glicko); wg=Glicko2Rating(**w.glicko); lg=Glicko2Rating(**l.glicko); wg.update(lg0,1.0); lg.update(wg0,0.0)
        w.glicko={"rating":wg.rating,"rd":wg.rd,"volatility":wg.volatility}; l.glicko={"rating":lg.rating,"rd":lg.rd,"volatility":lg.volatility}
        for p,old,score in ((w,w_elo_before,1),(l,l_elo_before,0)):
            se=p.surface_elo.get(surf,1500.0); opp=(l_elo_before if p is w else w_elo_before)
            e=1/(1+10**((opp-se)/400)); p.surface_elo[surf]=se+k*(score-e)
        sets=self._score_sets(self._get(r,'score','')); total_sets=len(sets)
        minutes=float(self._get(r,'minutes',0) or 0)
        # Aggregate service/return point proxies from completed match stats.
        def num(v):
            try:
                x=float(v)
                return 0.0 if math.isnan(x) else x
            except: return 0.0
        w_svpt=num(self._get(r,'w_svpt',0)); l_svpt=num(self._get(r,'l_svpt',0))
        w_1in=num(self._get(r,'w_1stIn',0)); l_1in=num(self._get(r,'l_1stIn',0))
        w_1won=num(self._get(r,'w_1stWon',0)); l_1won=num(self._get(r,'l_1stWon',0))
        w_2won=num(self._get(r,'w_2ndWon',0)); l_2won=num(self._get(r,'l_2ndWon',0))
        w_serv=max(1,w_svpt); l_serv=max(1,l_svpt)
        w.service_points += int(w_serv); w.service_points_won += int(w_1won+w_2won)
        l.service_points += int(l_serv); l.service_points_won += int(l_1won+l_2won)
        # Opponent's service points become return opportunities.
        w.return_points += int(l_serv); w.return_points_won += int(max(0,l_serv-(l_1won+l_2won)))
        l.return_points += int(w_serv); l.return_points_won += int(max(0,w_serv-(w_1won+w_2won)))
        for p,win,opp in ((w,1,l_elo_before),(l,0,w_elo_before)):
            p.wins += win; p.losses += 1-win
            p.surface_wins[surf]=p.surface_wins.get(surf,0)+win; p.surface_losses[surf]=p.surface_losses.get(surf,0)+1-win
            p.recent.append({"date":str(d.date()),"win":win,"surface":surf,"minutes":minutes,"opp_elo":opp,"sets":total_sets})
            p.opp_elos.append(opp); p.last_match=str(d.date())
        # Rebuild recent workload cheaply from the last 50 recorded matches.
        for p in (w,l):
            recent=list(p.recent); now=d
            p.matches_7d=sum((now-pd.Timestamp(x['date'])).days<=7 for x in recent)
            p.matches_30d=sum((now-pd.Timestamp(x['date'])).days<=30 for x in recent)
            p.minutes_7d=sum(x['minutes'] for x in recent if (now-pd.Timestamp(x['date'])).days<=7)
            p.minutes_30d=sum(x['minutes'] for x in recent if (now-pd.Timestamp(x['date'])).days<=30)
            p.sets_30d=sum(x['sets'] for x in recent if (now-pd.Timestamp(x['date'])).days<=30)
        # H2H, from perspective of each player.
        wk=lname.lower(); lk=wname.lower()
        w.h2h[wk]=w.h2h.get(wk,[])+[1]; l.h2h[lk]=l.h2h.get(lk,[])+[0]

    def get(self,name):
        key=str(name).strip().lower()
        if key in self.players: return self.players[key]
        # tolerant substring match
        hits=[p for k,p in self.players.items() if key in k or k in key]
        return hits[0] if len(hits)==1 else None
    def matchup_h2h(self,p1,p2,surface=None):
        if not p1 or not p2: return {"matches":0,"p1_wins":0,"p2_wins":0,"p1_rate":.5}
        vals=p1.h2h.get(p2.name.lower(),[])
        return {"matches":len(vals),"p1_wins":sum(vals),"p2_wins":len(vals)-sum(vals),"p1_rate":sum(vals)/len(vals) if vals else .5}
    def snapshot(self,p1,p2,surface,today=None,best_of=3):
        a=self.get(p1); b=self.get(p2)
        if a is None or b is None: return None
        today=pd.Timestamp(today or self.max_date or pd.Timestamp.utcnow())
        days_a=(today-pd.Timestamp(a.last_match)).days if a.last_match else 365
        days_b=(today-pd.Timestamp(b.last_match)).days if b.last_match else 365
        h=self.matchup_h2h(a,b,surface)
        sf=lambda p: p.surface_elo.get(surface,1500.0)
        return {
            "p1_name":a.name,"p2_name":b.name,"p1_elo":a.elo,"p2_elo":b.elo,"elo_diff":a.elo-b.elo,
            "p1_glicko":a.glicko.get("rating",1500.0),"p2_glicko":b.glicko.get("rating",1500.0),"glicko_diff":a.glicko.get("rating",1500.0)-b.glicko.get("rating",1500.0),
            "p1_rd":a.glicko.get("rd",350.0),"p2_rd":b.glicko.get("rd",350.0),"rd_diff":a.glicko.get("rd",350.0)-b.glicko.get("rd",350.0),
            "p1_surface_elo":sf(a),"p2_surface_elo":sf(b),"surface_elo_diff":sf(a)-sf(b),
            "p1_form5":a.form(5,surface,today),"p2_form5":b.form(5,surface,today),
            "p1_form10":a.form(10,surface,today),"p2_form10":b.form(10,surface,today),
            "p1_form20":a.form(20,surface,today),"p2_form20":b.form(20,surface,today),
            "form_diff":a.form(10,surface,today)-b.form(10,surface,today),
            "p1_service":a.service_rate(),"p2_service":b.service_rate(),"service_diff":a.service_rate()-b.service_rate(),
            "p1_return":a.return_rate(),"p2_return":b.return_rate(),"return_diff":a.return_rate()-b.return_rate(),
            "p1_opp_quality":a.opponent_quality(),"p2_opp_quality":b.opponent_quality(),
            "p1_fatigue":a.minutes_30d+2*a.minutes_7d,"p2_fatigue":b.minutes_30d+2*b.minutes_7d,
            "fatigue_diff":(a.minutes_30d+2*a.minutes_7d)-(b.minutes_30d+2*b.minutes_7d),
            "p1_rest_days":min(days_a,365),"p2_rest_days":min(days_b,365),"rest_diff":min(days_a,365)-min(days_b,365),
            "p1_matches_30d":a.matches_30d,"p2_matches_30d":b.matches_30d,"matches30_diff":a.matches_30d-b.matches_30d,
            "p1_sets_30d":a.sets_30d,"p2_sets_30d":b.sets_30d,"sets30_diff":a.sets_30d-b.sets_30d,
            "h2h_p1_rate":h["p1_rate"],"h2h_matches":h["matches"],
            "best_of":best_of,"surface_code":{"Hard":0,"Clay":1,"Grass":2,"Carpet":3}.get(surface,0),
            "p1_wins":a.wins,"p1_losses":a.losses,"p2_wins":b.wins,"p2_losses":b.losses,
        }

    def save(self,path):
        data={"max_date":str(self.max_date) if self.max_date is not None else None,"players":{k:p.to_dict() for k,p in self.players.items()}}
        Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    @classmethod
    def load(cls,path):
        obj=cls(); data=json.loads(Path(path).read_text(encoding='utf-8')); obj.max_date=pd.Timestamp(data['max_date']) if data.get('max_date') else None
        for k,d in data['players'].items():
            p=PlayerState(
                name=d.get('name',k), player_id=d.get('player_id',''), elo=d.get('elo',1500.0),
                glicko=d.get('glicko',{"rating":1500.0,"rd":350.0,"volatility":0.06}),
                surface_glicko=d.get('surface_glicko',{}), surface_elo=d.get('surface_elo',{"Hard":1500.0,"Clay":1500.0,"Grass":1500.0,"Carpet":1500.0}),
                wins=d.get('wins',0), losses=d.get('losses',0), surface_wins=d.get('surface_wins',{}), surface_losses=d.get('surface_losses',{}),
                recent=deque(d.get('recent',[]),maxlen=50), h2h=d.get('h2h',{}), last_match=d.get('last_match'),
                minutes_7d=d.get('minutes_7d',0), minutes_30d=d.get('minutes_30d',0), matches_7d=d.get('matches_7d',0), matches_30d=d.get('matches_30d',0), sets_30d=d.get('sets_30d',0),
                service_points=d.get('service_points',0), service_points_won=d.get('service_points_won',0), return_points=d.get('return_points',0), return_points_won=d.get('return_points_won',0),
                opp_elos=deque(d.get('opp_elos',[]),maxlen=50))
            obj.players[k]=p; obj.aliases[k]=p.name
        return obj
