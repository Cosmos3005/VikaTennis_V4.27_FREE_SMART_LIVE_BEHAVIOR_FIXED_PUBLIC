from __future__ import annotations
from pathlib import Path
import joblib, numpy as np, pandas as pd
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, mean_absolute_error
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier, XGBRegressor

TOTAL_LINES=np.arange(17.5,40.5,1.0); HANDICAP_LINES=np.arange(-8.5,8.6,1.0)

class VikaModels:
    def __init__(self): self.models={}; self.feature_columns=[]; self.metrics={}; self.version='v4.2'; self.calibrator=None
    def _clean(self,df): return df.reindex(columns=self.feature_columns,fill_value=0).replace([np.inf,-np.inf],np.nan).fillna(0.0)
    def fit(self,train,valid,test):
        ignore={'target_win','target_total','target_diff','date','p1_name','p2_name','player1_id','player2_id'}
        self.feature_columns=[c for c in train.columns if c not in ignore]
        Xtr,Xv,Xt=self._clean(train),self._clean(valid),self._clean(test)
        ytr,yv,yt=train.target_win.astype(int),valid.target_win.astype(int),test.target_win.astype(int)
        cb=__import__('xgboost').callback.EarlyStopping(rounds=35,metric_name='logloss',data_name='validation_0',save_best=True)
        self.models['winner']=XGBClassifier(n_estimators=450,max_depth=4,learning_rate=.03,subsample=.85,colsample_bytree=.85,min_child_weight=8,reg_lambda=6,reg_alpha=.05,objective='binary:logistic',eval_metric='logloss',random_state=42,n_jobs=4,tree_method='hist',callbacks=[cb])
        self.models['winner'].fit(Xtr,ytr,eval_set=[(Xv,yv)],verbose=False)
        pv_raw=self.models['winner'].predict_proba(Xv)[:,1]; pt_raw=self.models['winner'].predict_proba(Xt)[:,1]
        candidate_cal=LogisticRegression(C=1.0,solver='lbfgs').fit(pv_raw.reshape(-1,1),yv)
        pv_cal=candidate_cal.predict_proba(pv_raw.reshape(-1,1))[:,1]
        # Calibration is itself validated: never deploy it if it worsens validation logloss.
        if log_loss(yv,pv_cal) <= log_loss(yv,pv_raw):
            self.calibrator=candidate_cal; pv=pv_cal; pt=self.calibrator.predict_proba(pt_raw.reshape(-1,1))[:,1]; calibration_used=True
        else:
            self.calibrator=None; pv=pv_raw; pt=pt_raw; calibration_used=False
        self.metrics['winner']={'valid_acc':float(accuracy_score(yv,pv>=.5)),'valid_logloss':float(log_loss(yv,pv)),'valid_brier':float(brier_score_loss(yv,pv)),'test_acc':float(accuracy_score(yt,pt>=.5)),'test_logloss':float(log_loss(yt,pt)),'test_brier':float(brier_score_loss(yt,pt)),'raw_test_logloss':float(log_loss(yt,pt_raw)),'raw_test_brier':float(brier_score_loss(yt,pt_raw)),'calibration_used':calibration_used,'valid_raw_logloss':float(log_loss(yv,pv_raw)),'valid_calibrated_logloss':float(log_loss(yv,pv_cal)),'best_iteration':int(getattr(self.models['winner'],'best_iteration',-1))}
        for name,target in [('total','target_total'),('handicap','target_diff')]:
            cb2=__import__('xgboost').callback.EarlyStopping(rounds=30,metric_name='mae',data_name='validation_0',save_best=True)
            m=XGBRegressor(n_estimators=350,max_depth=4,learning_rate=.03,subsample=.85,colsample_bytree=.85,min_child_weight=8,reg_lambda=6,objective='reg:squarederror',eval_metric='mae',random_state=42,n_jobs=4,tree_method='hist',callbacks=[cb2])
            m.fit(Xtr,train[target],eval_set=[(Xv,valid[target])],verbose=False); pred=m.predict(Xv); self.models[name]=m; self.metrics[name]={'valid_mae':float(mean_absolute_error(valid[target],pred)),'best_iteration':int(getattr(m,'best_iteration',-1))}
        return self.metrics
    def predict(self,features):
        X=self._clean(features); raw=float(self.models['winner'].predict_proba(X)[:,1][0]); cal=getattr(self,'calibrator',None); p=float(cal.predict_proba(np.array([[raw]]))[:,1][0]) if cal is not None else raw; total=float(self.models['total'].predict(X)[0]); diff=float(self.models['handicap'].predict(X)[0]); return {'p1_win':p,'p2_win':1-p,'raw_p1_win':raw,'expected_total':total,'expected_diff':diff}
    def save(self,path='models/vika_models_v4.joblib'):
        Path(path).parent.mkdir(parents=True,exist_ok=True); joblib.dump(self,path)
    @classmethod
    def load(cls,path): return joblib.load(path)
