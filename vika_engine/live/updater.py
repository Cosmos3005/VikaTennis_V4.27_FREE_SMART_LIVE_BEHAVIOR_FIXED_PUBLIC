from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import math

@dataclass
class LiveState:
    match_id: str
    p1: str=''; p2: str=''; p1_sets:int=0; p2_sets:int=0; p1_games:int=0; p2_games:int=0; server:int=0; point_score:str=''; p1_probability:float=0.5; updated_at:str=''

class LiveUpdater:
    """Transforms provider score frames into a stable state and updates probability without overwriting the pre-match prior."""
    def __init__(self,pre_match_prob): self.prior=float(pre_match_prob)
    def update(self,frame):
        # SDK objects and dict payloads are both accepted.
        if hasattr(frame,'model_dump'): d=frame.model_dump()
        elif hasattr(frame,'__dict__'): d=frame.__dict__
        else: d=frame or {}
        score=d.get('score',d); sets=score.get('sets',[0,0]) if isinstance(score,dict) else [0,0]
        games=score.get('games',[[],[]]) if isinstance(score,dict) else [[],[]]
        p1g=sum(games[0]) if games and isinstance(games[0],list) else 0; p2g=sum(games[1]) if games and isinstance(games[1],list) else 0
        # If API supplies its own model probability, use it as observed live signal; otherwise a conservative score update.
        api_p=d.get('win_probability_p1')
        if api_p is not None: prob=float(api_p)
        else:
            margin=(sets[0]-sets[1])*0.28+(p1g-p2g)*0.025
            prob=1/(1+math.exp(-4*((self.prior-.5)+margin)))
        return LiveState(str(d.get('match_id','')),str(d.get('p1',d.get('player1',''))),str(d.get('p2',d.get('player2',''))),int(sets[0]),int(sets[1]),int(p1g),int(p2g),int(score.get('server',0) or 0) if isinstance(score,dict) else 0,str(score.get('point_score','')) if isinstance(score,dict) else '',max(.001,min(.999,prob)),datetime.now(timezone.utc).isoformat())
