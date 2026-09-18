import argparse, json
import pandas as pd
from vika_engine.models import VikaModels
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss

ap=argparse.ArgumentParser(); ap.add_argument('--source',default='data/v42_features.csv'); ap.add_argument('--out',default='models/vika_models_v42.joblib'); ap.add_argument('--report',default='models/v42_report.json'); a=ap.parse_args()
ds=pd.read_csv(a.source,parse_dates=['date'],low_memory=False).sort_values('date').reset_index(drop=True)
dates=ds.date.dt.normalize().unique(); c1=dates[int(len(dates)*.70)]; c2=dates[int(len(dates)*.85)]
tr=ds[ds.date<=c1]; va=ds[(ds.date>c1)&(ds.date<=c2)]; te=ds[ds.date>c2]
m=VikaModels(); metrics=m.fit(tr,va,te); m.version='v4.2-challenger'; m.save(a.out)
# simple rank baseline on the untouched test period
rankp=(1/(1+10**((te.p1_rank-te.p2_rank)/400))).clip(.001,.999)
y=te.target_win.astype(int)
metrics['baseline_rank']={'test_acc':float(accuracy_score(y,rankp>=.5)),'test_logloss':float(log_loss(y,rankp)),'test_brier':float(brier_score_loss(y,rankp))}
metrics['dataset']={'train':len(tr),'valid':len(va),'test':len(te),'train_end':str(c1),'valid_end':str(c2),'test_start':str(te.date.min()),'test_end':str(te.date.max())}
open(a.report,'w').write(json.dumps(metrics,indent=2,default=float)); print(json.dumps(metrics,indent=2,default=float))
