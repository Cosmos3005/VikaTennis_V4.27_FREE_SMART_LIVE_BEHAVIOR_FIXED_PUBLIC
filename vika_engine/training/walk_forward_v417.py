from __future__ import annotations
import json, math
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from xgboost import XGBClassifier
from xgboost.callback import EarlyStopping
from .live_model_v47 import Snapshot, FEATURES, _frame


def _metrics(y, p):
    y=np.asarray(y,dtype=int); p=np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)
    return {'n':int(len(y)), 'accuracy':float(accuracy_score(y,p>=.5)),
            'brier':float(brier_score_loss(y,p)), 'log_loss':float(log_loss(y,p,labels=[0,1]))}


def _match_dates(snaps: Iterable[Snapshot]):
    out={}
    for s in snaps:
        d=pd.Timestamp(s.date) if s.date else pd.NaT
        if s.match_id not in out or (pd.notna(d) and (pd.isna(out[s.match_id]) or d < out[s.match_id])):
            out[s.match_id]=d
    return out


def _partition(snaps, train_end, test_start, test_end=None):
    dates=_match_dates(snaps)
    train_ids={m for m,d in dates.items() if pd.notna(d) and d <= pd.Timestamp(train_end)}
    test_ids={m for m,d in dates.items() if pd.notna(d) and d >= pd.Timestamp(test_start) and (test_end is None or d <= pd.Timestamp(test_end))}
    return [s for s in snaps if s.match_id in train_ids], [s for s in snaps if s.match_id in test_ids]


def _fit(train, valid_days=120, seed=42):
    dates=_match_dates(train)
    ordered=sorted(dates, key=lambda m: (pd.isna(dates[m]), dates[m] if pd.notna(dates[m]) else pd.Timestamp.max, m))
    if len(ordered)<20: raise ValueError('Need at least 20 matches for a walk-forward training fold')
    cutoff=dates[ordered[max(0,len(ordered)-1)]] - pd.Timedelta(days=valid_days)
    tr_ids={m for m in ordered if pd.notna(dates[m]) and dates[m] < cutoff}
    va_ids={m for m in ordered if pd.notna(dates[m]) and dates[m] >= cutoff}
    if len(tr_ids)<10 or len(va_ids)<5:
        n=max(1,int(len(ordered)*.8)); tr_ids=set(ordered[:n]); va_ids=set(ordered[n:])
    tr=[s for s in train if s.match_id in tr_ids]; va=[s for s in train if s.match_id in va_ids]
    Xtr,ytr,_=_frame(tr); Xv,yv,_=_frame(va)
    clf=XGBClassifier(n_estimators=1200,max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.85,
        reg_lambda=2.0,min_child_weight=5,objective='binary:logistic',eval_metric='logloss',tree_method='hist',
        random_state=seed,n_jobs=2,callbacks=[EarlyStopping(rounds=60,save_best=True)])
    clf.fit(Xtr,ytr,eval_set=[(Xv,yv)],verbose=False)
    return clf, len(tr_ids), len(va_ids)


def evaluate_fold(snaps, train_end, test_start, test_end=None, seed=42):
    train, test=_partition(snaps,train_end,test_start,test_end)
    if len({s.match_id for s in test}) < 5: return {'status':'skipped','reason':'fewer_than_5_test_matches','train_end':train_end,'test_start':test_start,'test_end':test_end}
    clf,ntr,nva=_fit(train,seed=seed)
    Xt,yt,_=_frame(test); p=clf.predict_proba(Xt)[:,1]
    prior=np.array([1/(1+math.exp(-float(s.features.get('prior_logit',0)))) for s in test])
    return {'status':'ok','train_end':train_end,'test_start':test_start,'test_end':test_end,
            'train_matches':ntr,'validation_matches':nva,'test_matches':len({s.match_id for s in test}),
            'test_snapshots':len(test),'live_xgb':_metrics(yt,p),'pre_match_prior':_metrics(yt,prior),
            'improvement_logloss':float(_metrics(yt,prior)['log_loss']-_metrics(yt,p)['log_loss']),
            'improvement_brier':float(_metrics(yt,prior)['brier']-_metrics(yt,p)['brier'])}


def run_walk_forward(snaps, folds=None):
    folds=folds or [
        {'train_end':'2023-12-31','test_start':'2024-01-01','test_end':'2024-12-31'},
        {'train_end':'2024-12-31','test_start':'2025-01-01','test_end':'2025-12-31'},
        {'train_end':'2025-12-31','test_start':'2026-01-01','test_end':'2026-12-31'},
    ]
    results=[evaluate_fold(snaps,**f,seed=42+i) for i,f in enumerate(folds)]
    valid=[r for r in results if r.get('status')=='ok']
    if valid:
        avg_x=np.mean([r['live_xgb']['log_loss'] for r in valid]); avg_p=np.mean([r['pre_match_prior']['log_loss'] for r in valid])
        avg_bx=np.mean([r['live_xgb']['brier'] for r in valid]); avg_bp=np.mean([r['pre_match_prior']['brier'] for r in valid])
    else: avg_x=avg_p=avg_bx=avg_bp=float('nan')
    champion='live_xgb' if valid and (avg_x,avg_bx)<(avg_p,avg_bp) else 'pre_match_prior'
    return {'version':'v4.17','selection':'mean walk-forward log_loss, then brier','champion':champion,
            'folds':results,'aggregate':{'folds_ok':len(valid),'mean_live_log_loss':None if not valid else float(avg_x),
            'mean_prior_log_loss':None if not valid else float(avg_p),'mean_live_brier':None if not valid else float(avg_bx),
            'mean_prior_brier':None if not valid else float(avg_bp)}}
