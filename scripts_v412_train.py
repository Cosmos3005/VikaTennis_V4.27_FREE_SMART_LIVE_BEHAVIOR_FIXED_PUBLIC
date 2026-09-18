from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
from vika_engine.models import VikaModels
from sklearn.metrics import accuracy_score,log_loss,brier_score_loss

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',default='data/v412_features.csv.gz'); ap.add_argument('--out',default='models/vika_models_v412.joblib'); ap.add_argument('--report',default='models/v412_model_report.json'); a=ap.parse_args()
    ds=pd.read_csv(a.source,parse_dates=['date'],low_memory=False).sort_values('date').reset_index(drop=True)
    dates=ds.date.dt.normalize().drop_duplicates().tolist(); n=len(dates); c1=dates[int(n*.70)]; c2=dates[int(n*.85)]
    tr=ds[ds.date<=c1]; va=ds[(ds.date>c1)&(ds.date<=c2)]; te=ds[ds.date>c2]
    m=VikaModels(); metrics=m.fit(tr,va,te); m.version='v4.12-archive-engine'; m.save(a.out)
    rankp=(1/(1+10**((te.p1_rank-te.p2_rank)/400))).clip(.001,.999) if 'p1_rank' in te else pd.Series(.5,index=te.index)
    y=te.target_win.astype(int); metrics['baseline_rank']={'test_acc':float(accuracy_score(y,rankp>=.5)),'test_logloss':float(log_loss(y,rankp)),'test_brier':float(brier_score_loss(y,rankp))}
    metrics['dataset']={'rows':len(ds),'train':len(tr),'valid':len(va),'test':len(te),'train_end':str(c1),'valid_end':str(c2),'test_start':str(te.date.min()),'test_end':str(te.date.max())}
    Path(a.report).write_text(json.dumps(metrics,ensure_ascii=False,indent=2,default=float),encoding='utf-8'); print(json.dumps(metrics,ensure_ascii=False,indent=2,default=float))
if __name__=='__main__': main()
