from __future__ import annotations
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score,brier_score_loss,log_loss
from xgboost import XGBClassifier
from xgboost.callback import EarlyStopping
from .live_model_v47 import LiveSnapshotBuilderV47,_frame
from .champion_live import pre_match_probs,conservative_mc_proxy

def _metrics(y,p):
    if not y:return {'n_snapshots':0,'accuracy':0.0,'brier':0.0,'log_loss':0.0}
    p=np.clip(np.asarray(p,float),1e-6,1-1e-6)
    return {'n_snapshots':len(y),'accuracy':float(accuracy_score(y,p>=.5)),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1]))}

def _match_dates(snaps):
    out={}
    for s in snaps:
        d=pd.to_datetime(s.date,errors='coerce')
        if pd.isna(d):continue
        if s.match_id not in out or d<out[s.match_id]:out[s.match_id]=d
    return out

def _split(snaps,train_end,test_start,test_end,validation_days):
    md=_match_dates(snaps)
    train={m for m,d in md.items() if d<=train_end}; test={m for m,d in md.items() if test_start<=d<=test_end}
    vs=train_end-pd.Timedelta(days=validation_days-1); valid={m for m,d in md.items() if vs<=d<=train_end}
    fit=train-valid
    return ([s for s in snaps if s.match_id in fit],[s for s in snaps if s.match_id in valid],[s for s in snaps if s.match_id in test])

def _fit(tr,va,seed):
    X,y,_=_frame(tr); Xv,yv,_=_frame(va)
    if len(set(y))<2 or len(set(yv))<2:raise ValueError('walk-forward fold lacks both outcomes')
    clf=XGBClassifier(n_estimators=1200,max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.85,reg_lambda=2.0,min_child_weight=5,objective='binary:logistic',eval_metric='logloss',tree_method='hist',random_state=seed,n_jobs=2,callbacks=[EarlyStopping(rounds=60,save_best=True)])
    clf.fit(X,y,eval_set=[(Xv,yv)],verbose=False); return clf

def run_walk_forward(snaps,validation_days=120,seed=42):
    folds=[('2024','2023-12-31','2024-01-01','2024-12-31'),('2025','2024-12-31','2025-01-01','2025-12-31'),('2026_ytd','2025-12-31','2026-01-01','2026-09-08')]
    results=[]
    for i,(name,te,ts,tx) in enumerate(folds):
        tr,va,test=_split(snaps,pd.Timestamp(te),pd.Timestamp(ts),pd.Timestamp(tx),validation_days)
        base={'fold':name,'train_matches':len({s.match_id for s in tr}),'validation_matches':len({s.match_id for s in va}),'test_matches':len({s.match_id for s in test}),'train_snapshots':len(tr),'validation_snapshots':len(va),'test_snapshots':len(test)}
        if len(tr)<100 or len(va)<20 or len(test)<20:
            base['status']='insufficient_data';results.append(base);continue
        clf=_fit(tr,va,seed+i); X,_,_=_frame(test); p=clf.predict_proba(X)[:,1].tolist(); y=[s.target for s in test]; prior=pre_match_probs(test); proxy=[conservative_mc_proxy(s) for s in test]; blend=[.65*a+.35*b for a,b in zip(p,proxy)]
        base.update({'status':'ok','train_end':te,'test_start':ts,'test_end':tx,'best_iteration':int(getattr(clf,'best_iteration',-1)),'models':{'pre_match_v42_prior':_metrics(y,prior),'v47_live_xgb':_metrics(y,p),'v47_plus_live_state_proxy':_metrics(y,blend)}});results.append(base)
    return {'folds':results,'total_folds':len(results),'successful_folds':sum(r.get('status')=='ok' for r in results)}

def aggregate(report):
    rows=defaultdict(list)
    for f in report['folds']:
        if f.get('status')=='ok':
            for n,m in f['models'].items():rows[n].append(m)
    models={}
    for n,vs in rows.items():
        total=sum(v['n_snapshots'] for v in vs)
        models[n]={'folds':len(vs),'n_snapshots':total,'mean_accuracy':float(np.mean([v['accuracy'] for v in vs])),'mean_brier':float(np.mean([v['brier'] for v in vs])),'mean_log_loss':float(np.mean([v['log_loss'] for v in vs])),'weighted_brier':float(sum(v['brier']*v['n_snapshots'] for v in vs)/total),'weighted_log_loss':float(sum(v['log_loss']*v['n_snapshots'] for v in vs)/total)}
    report['models']=models;report['ranking']=[n for n,_ in sorted(models.items(),key=lambda kv:(kv[1]['weighted_log_loss'],kv[1]['weighted_brier']))];report['champion']=report['ranking'][0] if report['ranking'] else None;report['champion_rule']='lowest weighted walk-forward log loss, then weighted brier';return report

def run_from_jsonl(path,max_snapshots_per_match=80):
    from scripts_v47_train_live import load_jsonl
    return LiveSnapshotBuilderV47(max_snapshots_per_match=max_snapshots_per_match,prior_provider=None).build(load_jsonl(path))
