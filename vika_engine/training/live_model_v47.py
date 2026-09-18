from __future__ import annotations
import json, math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from xgboost import XGBClassifier

FEATURES = [
    'prior_logit','sets_diff','games_diff','games_total','set_margin_abs',
    'server_p1','point_diff','point_total','elapsed_minutes','seq_log',
    'momentum_ewma','momentum_sample','momentum_pressure',
]

def _get(x: Any, *names, default=None):
    if isinstance(x, dict):
        for n in names:
            if n in x and x[n] is not None:
                return x[n]
    else:
        for n in names:
            if hasattr(x, n):
                v = getattr(x, n)
                if v is not None:
                    return v
    return default

def _num(v, default=0.0):
    try: return float(v)
    except Exception: return default

def _clamp(p): return max(1e-5, min(1-1e-5, float(p)))

def _logit(p):
    p=_clamp(p); return math.log(p/(1-p))

def _games_total_and_diff(games):
    if games is None: return 0, 0
    if isinstance(games, dict):
        games=[games.get('p1', games.get('player1', 0)), games.get('p2', games.get('player2', 0))]
    def side(v):
        if isinstance(v, (list, tuple)):
            return sum(_num(x) for x in v)
        return _num(v)
    a,b=side(games[0]),side(games[1]) if len(games)>1 else 0
    return a-b,a+b

def _score_diff(row):
    score=_get(row,'score',default=None)
    src=score if score is not None else row
    sets=_get(src,'sets',default=[0,0]) or [0,0]
    try: sets_diff=_num(sets[0])-_num(sets[1])
    except Exception: sets_diff=0.0
    games=_get(src,'games',default=[0,0]) or [0,0]
    games_diff,games_total=_games_total_and_diff(games)
    return sets_diff,games_diff,games_total

def _point_score(row):
    raw=_get(row,'point_score','points','point',default=None)
    if isinstance(raw, dict):
        a=_num(_get(raw,'p1','player1',default=0)); b=_num(_get(raw,'p2','player2',default=0)); return a-b,a+b
    if isinstance(raw,(list,tuple)) and len(raw)>=2:
        return _num(raw[0])- _num(raw[1]), _num(raw[0])+_num(raw[1])
    if isinstance(raw,str):
        s=raw.strip().lower().replace('all','40').replace('adv','50')
        parts=[p.strip() for p in s.replace(':','-').split('-')]
        if len(parts)==2:
            mp={'0':0,'15':1,'30':2,'40':3,'game':4,'50':4}
            if parts[0] in mp and parts[1] in mp:
                a,b=mp[parts[0]],mp[parts[1]]; return a-b,a+b
    return 0.0,0.0

def _server_p1(row):
    s=_get(row,'server','serving_player','server_index',default=0)
    if isinstance(s,str):
        z=s.lower()
        if z in ('p1','player1','1','a'): return 1.0
        if z in ('p2','player2','2','b'): return 0.0
    return 1.0 if _num(s)==1 else 0.0

def _point_winner(row):
    w=_get(row,'point_winner','winner','pointWinner',default=None)
    if isinstance(w,str):
        z=w.lower()
        if z in ('p1','player1','1','a'): return 1
        if z in ('p2','player2','2','b'): return -1
    if _num(w,99) in (1,2): return 1 if _num(w)==1 else -1
    return 0

def _timestamp_minutes(ts, first_ts):
    if not ts or not first_ts: return 0.0
    try:
        a=pd.Timestamp(ts); b=pd.Timestamp(first_ts)
        return max(0.0,(a-b).total_seconds()/60.0)
    except Exception: return 0.0

@dataclass
class Snapshot:
    match_id: str
    date: str
    seq: int
    target: int
    coverage: str
    features: dict

class LiveSnapshotBuilderV47:
    """Builds causal historical live snapshots.

    Each row predicts the final match winner using only state available in that row.
    Provider model probabilities and provider 'danger' fields are deliberately excluded
    from features so Vika does not learn to imitate the external vendor.
    """
    def __init__(self, checkpoint_every=1, max_snapshots_per_match=80, prior_provider: Callable|None=None):
        self.checkpoint_every=max(1,int(checkpoint_every)); self.max_snapshots_per_match=max(1,int(max_snapshots_per_match)); self.prior_provider=prior_provider

    def _outcome(self, match):
        w=_get(match,'winner',default=None)
        if str(w).lower() in ('1','p1','player1','a'): return 1
        if str(w).lower() in ('2','p2','player2','b'): return 0
        return None

    def build_match(self, match_id: str, tape: dict) -> list[Snapshot]:
        match=tape.get('match',{}) if isinstance(tape,dict) else {}
        rows=tape.get('tape',tape.get('points',[])) if isinstance(tape,dict) else []
        outcome=self._outcome(match)
        if outcome is None or not rows: return []
        p1=_get(match,'player1_name',default='P1'); p2=_get(match,'player2_name',default='P2')
        prior=0.5
        if self.prior_provider:
            try: prior=float(self.prior_provider(p1,p2))
            except Exception: prior=0.5
        prior=_clamp(prior)
        first_ts=_get(rows[0],'timestamp',default=None)
        coverage=str(_get(tape.get('meta',{}),'coverage',default=_get(match,'coverage',default='unknown')))
        ewma=0.0; sample=0
        step=max(1, math.ceil(len(rows)/self.max_snapshots_per_match))
        out=[]
        for i,row in enumerate(rows,1):
            w=_point_winner(row)
            if w:
                sample+=1; ewma=0.90*ewma+0.10*w
            if i % self.checkpoint_every != 0 and i != len(rows): continue
            if (i//step)*step != i and i != len(rows): continue
            sd,gd,gt=_score_diff(row); pdiff,ptotal=_point_score(row)
            seq=int(_num(_get(row,'seq',default=i),i))
            feats={
                'prior_logit':_logit(prior),'sets_diff':sd,'games_diff':gd,'games_total':gt,
                'set_margin_abs':abs(sd),'server_p1':_server_p1(row),'point_diff':pdiff,'point_total':ptotal,
                'elapsed_minutes':_timestamp_minutes(_get(row,'timestamp',default=None),first_ts),
                'seq_log':math.log1p(max(0,seq)),'momentum_ewma':ewma,'momentum_sample':min(sample,100),
                'momentum_pressure':ewma*min(1.0,sample/12.0),
            }
            out.append(Snapshot(str(match_id),str(_get(match,'date','start_time','scheduled_at',default='')),seq,int(outcome),coverage,feats))
        return out

    def build(self, matches: Iterable[tuple[str,dict]]) -> list[Snapshot]:
        out=[]
        for mid,tape in matches: out.extend(self.build_match(mid,tape))
        return out

class CalibratedLiveModel:
    """Serializable wrapper applying a Platt calibrator to a base live model."""
    def __init__(self, base_model, calibrator, version='v4.16-live-calibrated'):
        self.base_model=base_model; self.calibrator=calibrator; self.version=version
    def predict_proba(self, features: dict) -> float:
        p=float(self.base_model.predict_proba(features))
        z=math.log(_clamp(p)/(1-_clamp(p)))
        return float(self.calibrator.predict_proba(np.asarray([[z]],dtype=float))[0,1])
    def save(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True); joblib.dump(self,path)
    @classmethod
    def load(cls,path): return joblib.load(path)

class LiveModelV47:
    def __init__(self, estimator, feature_columns=FEATURES, version='v4.7-live-xgb'):
        self.estimator=estimator; self.feature_columns=list(feature_columns); self.version=version
    def predict_proba(self, features: dict) -> float:
        x=pd.DataFrame([{k:float(features.get(k,0.0)) for k in self.feature_columns}],columns=self.feature_columns)
        return float(self.estimator.predict_proba(x)[0,1])
    def save(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True); joblib.dump(self,path)
    @classmethod
    def load(cls,path): return joblib.load(path)

def _frame(snaps):
    X=pd.DataFrame([{k:s.features.get(k,0.0) for k in FEATURES} for s in snaps],columns=FEATURES)
    y=np.array([s.target for s in snaps],dtype=int)
    dates=pd.to_datetime([s.date for s in snaps],errors='coerce')
    # Missing dates are placed after dated samples, but split remains by whole match IDs.
    return X,y,dates

def _metrics(model,X,y):
    if len(y)==0:return {'n':0}
    p=model.predict_proba(X)[:,1]
    return {'n':int(len(y)),'accuracy':float(accuracy_score(y,p>=.5)),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1]))}

def train_live_model(snaps: list[Snapshot], model_path, valid_fraction=.20, test_fraction=.20, random_state=42):
    if len(snaps)<100: raise ValueError('Need at least 100 historical live snapshots for V4.7 training.')
    # Split by match, never by individual snapshots, to avoid the same match appearing in train and test.
    mids=sorted({s.match_id for s in snaps})
    if len(mids)<10: raise ValueError('Need at least 10 unique matches for chronological live training.')
    # Use match date where possible; fallback to input order for undated archives.
    match_date={}
    for s in snaps:
        d=pd.Timestamp(s.date) if s.date and str(s.date) not in ('NaT','None','') else pd.NaT
        if s.match_id not in match_date or (pd.notna(d) and (pd.isna(match_date[s.match_id]) or d<match_date[s.match_id])): match_date[s.match_id]=d
    mids=sorted(mids,key=lambda m:(pd.isna(match_date[m]),match_date[m] if pd.notna(match_date[m]) else pd.Timestamp.max,m))
    n=len(mids); ntr=max(1,int(n*(1-valid_fraction-test_fraction))); nv=max(1,int(n*valid_fraction))
    train_ids=set(mids[:ntr]); valid_ids=set(mids[ntr:ntr+nv]); test_ids=set(mids[ntr+nv:])
    tr=[s for s in snaps if s.match_id in train_ids]; va=[s for s in snaps if s.match_id in valid_ids]; te=[s for s in snaps if s.match_id in test_ids]
    Xtr,ytr,_=_frame(tr); Xv,yv,_=_frame(va); Xt,yt,_=_frame(te)
    from xgboost.callback import EarlyStopping
    clf=XGBClassifier(n_estimators=1200,max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.85,
                      reg_lambda=2.0,min_child_weight=5,objective='binary:logistic',eval_metric='logloss',
                      tree_method='hist',random_state=random_state,n_jobs=2,
                      callbacks=[EarlyStopping(rounds=60,save_best=True)])
    clf.fit(Xtr,ytr,eval_set=[(Xv,yv)],verbose=False)
    model=LiveModelV47(clf)
    metrics={'train':_metrics(clf,Xtr,ytr),'validation':_metrics(clf,Xv,yv),'test':_metrics(clf,Xt,yt),
             'baseline':{'brier':.25,'log_loss':math.log(2),'accuracy':.5},
             'matches':{'train':len(train_ids),'validation':len(valid_ids),'test':len(test_ids)},
             'snapshots':{'train':len(tr),'validation':len(va),'test':len(te)},
             'best_iteration':int(getattr(clf,'best_iteration',-1))}
    model.save(model_path)
    return model,metrics
