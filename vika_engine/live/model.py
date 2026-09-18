from __future__ import annotations
import math
from dataclasses import dataclass, asdict
from typing import Any
from .momentum import PointMomentum, MomentumSnapshot


def _clamp(x: float, lo: float = 0.001, hi: float = 0.999) -> float:
    return max(lo, min(hi, float(x)))

def _logit(p: float) -> float:
    p = _clamp(p)
    return math.log(p / (1.0 - p))

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))

def _extract(d: Any, *names, default=None):
    if isinstance(d, dict):
        for n in names:
            if n in d and d[n] is not None: return d[n]
    else:
        for n in names:
            if hasattr(d, n):
                v = getattr(d, n)
                if v is not None: return v
    return default

def _sets_games(score: Any):
    sets = _extract(score, "sets", default=[0, 0]) or [0, 0]
    games = _extract(score, "games", default=[0, 0]) or [0, 0]
    if isinstance(games, dict): games=[games.get("p1", games.get("player1",0)),games.get("p2",games.get("player2",0))]
    def norm(v):
        if isinstance(v,(list,tuple)): return sum(int(x) for x in v if str(x).lstrip('-').isdigit())
        try: return int(v)
        except Exception: return 0
    return int(sets[0]),int(sets[1]),norm(games[0]),norm(games[1])

@dataclass
class LiveFeatures:
    p1_sets:int; p2_sets:int; p1_games:int; p2_games:int
    server:int=0; point_p1:float|None=None; point_p2:float|None=None; elapsed_minutes:float=0.0
    p1_aces:float=0.0; p2_aces:float=0.0; p1_double_faults:float=0.0; p2_double_faults:float=0.0
    p1_break_points:float=0.0; p2_break_points:float=0.0; p1_break_points_won:float=0.0; p2_break_points_won:float=0.0
    p1_service_points_won:float=0.0; p2_service_points_won:float=0.0; p1_return_points_won:float=0.0; p2_return_points_won:float=0.0
    p1_win_probability_api:float|None=None

class LiveWinModel:
    def __init__(self, prior:float, momentum:PointMomentum|None=None):
        self.prior=_clamp(prior); self.momentum=momentum or PointMomentum()

    @classmethod
    def from_frame(cls, prior:float, frame:Any):
        d=frame if isinstance(frame,dict) else getattr(frame,'__dict__',{})
        score=d.get('score',d) if isinstance(d,dict) else d
        s1,s2,g1,g2=_sets_games(score)
        def num(*names):
            v=_extract(d,*names,default=0)
            try:return float(v or 0)
            except Exception:return 0.0
        v=_extract(d,'win_probability_p1','p1_win_probability',default=None)
        return LiveFeatures(s1,s2,g1,g2,int(num('server','serving_player','server_index')),None,None,num('elapsed_minutes','duration_minutes','minutes'),
            num('p1_aces','aces_p1','player1_aces'),num('p2_aces','aces_p2','player2_aces'),num('p1_double_faults','double_faults_p1','player1_double_faults'),num('p2_double_faults','double_faults_p2','player2_double_faults'),
            num('p1_break_points','break_points_p1','player1_break_points'),num('p2_break_points','break_points_p2','player2_break_points'),num('p1_break_points_won','break_points_won_p1','player1_break_points_won'),num('p2_break_points_won','break_points_won_p2','player2_break_points_won'),
            num('p1_service_points_won','service_points_won_p1','player1_service_points_won'),num('p2_service_points_won','service_points_won_p2','player2_service_points_won'),num('p1_return_points_won','return_points_won_p1','player1_return_points_won'),num('p2_return_points_won','return_points_won_p2','player2_return_points_won'),
            float(v) if v is not None else None)

    def update_point(self,event:Any):
        return self.momentum.update(event)

    def predict(self,f:LiveFeatures,momentum:MomentumSnapshot|None=None)->dict:
        set_margin=f.p1_sets-f.p2_sets; game_margin=f.p1_games-f.p2_games
        state_logit=1.75*set_margin+0.075*game_margin
        stat_logit=0.0; stat_weight=0.0
        if f.p1_service_points_won+f.p2_service_points_won>=20:
            stat_logit+=0.018*(f.p1_service_points_won-f.p2_service_points_won); stat_weight+=.35
        if f.p1_return_points_won+f.p2_return_points_won>=20:
            stat_logit+=0.018*(f.p1_return_points_won-f.p2_return_points_won); stat_weight+=.35
        bp=f.p1_break_points+f.p2_break_points
        if bp>=3: stat_logit+=.12*(f.p1_break_points_won-f.p2_break_points_won); stat_weight+=.30
        if f.p1_aces+f.p2_aces>=4: stat_logit+=.025*(f.p1_aces-f.p2_aces); stat_weight+=.10
        if f.p1_double_faults+f.p2_double_faults>=3: stat_logit-=.025*(f.p1_double_faults-f.p2_double_faults); stat_weight+=.10
        evidence_scale=min(1.0,.35+.13*max(0,set_margin!=0)+.012*min(30,abs(game_margin)))
        momentum=momentum or self.momentum.snapshot()
        # Momentum is capped so it cannot overpower score/prior with a small sample.
        m_scale=min(1.0,momentum.sample_size/18.0)
        momentum_logit=1.15*momentum.pressure*m_scale
        live_logit=_logit(self.prior)+evidence_scale*state_logit+min(1.,stat_weight)*stat_logit+momentum_logit
        model_p=_sigmoid(live_logit)
        api_p=f.p1_win_probability_api
        if api_p is not None:
            w=.15+.25*min(1.,(abs(set_margin)+abs(game_margin)/6.)/2.)
            model_p=_sigmoid((1-w)*_logit(model_p)+w*_logit(api_p))
        confidence=min(1.,.25+.18*abs(set_margin)+.03*min(10,abs(game_margin))+.01*min(20,bp)+.012*min(25,momentum.sample_size))
        return {'p1_win':_clamp(model_p),'p2_win':_clamp(1-model_p),'prior':self.prior,'state_logit':state_logit,'stat_logit':stat_logit,'momentum_logit':momentum_logit,'confidence':round(confidence,3),'momentum':asdict(momentum),'features':asdict(f)}
