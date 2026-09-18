from __future__ import annotations
from pathlib import Path
from typing import Any
import math
import joblib
from vika_engine.training.live_model_v47 import FEATURES, LiveModelV47, _score_diff, _point_score, _server_p1, _point_winner, _timestamp_minutes

class LiveMLAdapterV47:
    def __init__(self, path=None):
        candidates=[]
        if path: candidates.append(Path(path))
        candidates += [Path('models/vika_live_v417.joblib'), Path('models/vika_live_v416.joblib'), Path('models/vika_live_v47.joblib')]
        self.path=next((p for p in candidates if p.exists()), candidates[-1])
        self.model=None
        if self.path.exists():
            try:self.model=joblib.load(self.path)
            except Exception:self.model=None
    @property
    def available(self): return self.model is not None
    def predict(self, prior: float, frame: Any, state: dict|None=None) -> float|None:
        if not self.model:return None
        d=frame if isinstance(frame,dict) else getattr(frame,'__dict__',{})
        sd,gd,gt=_score_diff(d); pdiff,ptotal=_point_score(d)
        sample=int((state or {}).get('momentum_sample',0)); ewma=float((state or {}).get('momentum_ewma',0.0))
        w=_point_winner(d)
        if w: sample+=1; ewma=.90*ewma+.10*w
        features={'prior_logit':math.log(max(.00001,min(.99999,prior))/(1-max(.00001,min(.99999,prior)))),'sets_diff':sd,'games_diff':gd,'games_total':gt,
                  'set_margin_abs':abs(sd),'server_p1':_server_p1(d),'point_diff':pdiff,'point_total':ptotal,'elapsed_minutes':float((state or {}).get('elapsed_minutes',0)),
                  'seq_log':math.log1p(float(d.get('seq',0) or 0)),'momentum_ewma':ewma,'momentum_sample':min(sample,100),'momentum_pressure':ewma*min(1,sample/12)}
        return self.model.predict_proba(features)
