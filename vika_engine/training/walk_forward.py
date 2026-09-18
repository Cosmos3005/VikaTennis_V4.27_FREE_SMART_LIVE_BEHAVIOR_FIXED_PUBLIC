from __future__ import annotations
import pandas as pd
from sklearn.metrics import accuracy_score,log_loss,brier_score_loss

def chronological_splits(ds,train_frac=.70,valid_frac=.15):
    dates=sorted(pd.to_datetime(ds.date).dropna().unique()); n=len(dates)
    c1=dates[max(1,int(n*train_frac)-1)]; c2=dates[max(2,int(n*(train_frac+valid_frac))-1)]
    return ds[ds.date<=c1],ds[(ds.date>c1)&(ds.date<=c2)],ds[ds.date>c2]

def evaluate_binary(model,X,y):
    p=model.predict_proba(X)[:,1]; return {'accuracy':float(accuracy_score(y,p>=.5)),'log_loss':float(log_loss(y,p)),'brier':float(brier_score_loss(y,p))}
