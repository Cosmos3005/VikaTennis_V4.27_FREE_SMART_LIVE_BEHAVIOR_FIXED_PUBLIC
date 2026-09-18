from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from .live_model_v47 import LiveModelV47, CalibratedLiveModel, Snapshot, FEATURES, train_live_model, _frame


def _clip(p): return np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)

def _metrics(y,p):
    p=_clip(p); y=np.asarray(y,dtype=int)
    return {'n':int(len(y)), 'accuracy':float(accuracy_score(y,p>=.5)),
            'brier':float(brier_score_loss(y,p)), 'log_loss':float(log_loss(y,p,labels=[0,1]))}

def _split(snaps, valid_fraction=.20, test_fraction=.20):
    dates={}
    for s in snaps:
        d=np.datetime64(s.date[:10]) if s.date and len(s.date)>=10 else np.datetime64('NaT')
        old=dates.get(s.match_id)
        if old is None or (str(d)!='NaT' and (str(old)=='NaT' or d<old)): dates[s.match_id]=d
    mids=sorted(dates,key=lambda m:(str(dates[m])=='NaT', dates[m] if str(dates[m])!='NaT' else np.datetime64('9999-12-31')))
    n=len(mids); ntr=max(1,int(n*(1-valid_fraction-test_fraction))); nv=max(1,int(n*valid_fraction))
    return ([s for s in snaps if s.match_id in set(mids[:ntr])],
            [s for s in snaps if s.match_id in set(mids[ntr:ntr+nv])],
            [s for s in snaps if s.match_id in set(mids[ntr+nv:])])

def _prior(snaps):
    return np.array([1/(1+math.exp(-float(s.features.get('prior_logit',0)))) for s in snaps])

def _fit_platt(model, val):
    Xv,yv,_=_frame(val); pv=model.estimator.predict_proba(Xv)[:,1]
    cal=LogisticRegression(solver='lbfgs').fit(np.log(np.clip(pv,1e-6,1-1e-6)/(1-np.clip(pv,1e-6,1-1e-6))).reshape(-1,1),yv)
    return cal

def _apply_platt(model,cal,snaps):
    X,y,_=_frame(snaps); p=model.estimator.predict_proba(X)[:,1]; z=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6)))
    return cal.predict_proba(z.reshape(-1,1))[:,1]

def train_champion(snaps, output_model, report_path):
    tr,va,te=_split(snaps)
    if len({s.match_id for s in te})<5: raise ValueError('Need at least 5 test matches')
    # train_live_model re-splits internally; instead train directly on our explicit train/validation split
    Xtr,ytr,_=_frame(tr); Xv,yv,_=_frame(va); Xt,yt,_=_frame(te)
    from xgboost import XGBClassifier
    from xgboost.callback import EarlyStopping
    clf=XGBClassifier(n_estimators=1200,max_depth=4,learning_rate=.035,subsample=.85,colsample_bytree=.85,
        reg_lambda=2.0,min_child_weight=5,objective='binary:logistic',eval_metric='logloss',tree_method='hist',random_state=42,n_jobs=2,
        callbacks=[EarlyStopping(rounds=60,save_best=True)])
    clf.fit(Xtr,ytr,eval_set=[(Xv,yv)],verbose=False)
    model=LiveModelV47(clf,version='v4.16-live-xgb')
    Path(output_model).parent.mkdir(parents=True,exist_ok=True)
    pva=clf.predict_proba(Xv)[:,1]; pte=clf.predict_proba(Xt)[:,1]
    methods_val={'pre_match_prior':_prior(va),'live_xgb':pva}
    methods_test={'pre_match_prior':_prior(te),'live_xgb':pte}
    cal=_fit_platt(model,va)
    pva_cal=_apply_platt(model,cal,va); pte_cal=_apply_platt(model,cal,te)
    methods_val['live_xgb_calibrated']=pva_cal; methods_test['live_xgb_calibrated']=pte_cal
    ranking=sorted(methods_val,key=lambda k:(_metrics(yv,methods_val[k])['log_loss'],_metrics(yv,methods_val[k])['brier']))
    champion=ranking[0]
    if champion=='live_xgb_calibrated':
        CalibratedLiveModel(model,cal).save(output_model)
    else:
        model.save(output_model)
    report={'version':'v4.16','selection':'validation log_loss, then brier','champion':champion,
            'split_matches':{'train':len({s.match_id for s in tr}),'validation':len({s.match_id for s in va}),'test':len({s.match_id for s in te})},
            'split_snapshots':{'train':len(tr),'validation':len(va),'test':len(te)},
            'validation':{k:_metrics(yv,v) for k,v in methods_val.items()},
            'test':{k:_metrics(yt,v) for k,v in methods_test.items()},
            'calibration_used':champion=='live_xgb_calibrated',
            'model_path':str(output_model)}
    Path(report_path).parent.mkdir(parents=True,exist_ok=True); Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
