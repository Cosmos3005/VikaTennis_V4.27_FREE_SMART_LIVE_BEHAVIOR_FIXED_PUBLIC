import argparse, pandas as pd
from vika_engine.models import VikaModels
p=argparse.ArgumentParser(); p.add_argument('--source',default='data/v4_features.csv'); p.add_argument('--out',default='models/vika_models_v4.joblib'); a=p.parse_args()
ds=pd.read_csv(a.source,parse_dates=['date']).sort_values('date').reset_index(drop=True)
# Use only the modern era while preserving strict chronology.
ds=ds[ds.date.dt.year>=2020].copy()
dates=ds.date.sort_values().unique(); c1=dates[int(len(dates)*.70)]; c2=dates[int(len(dates)*.85)]
tr=ds[ds.date<=c1]; va=ds[(ds.date>c1)&(ds.date<=c2)]; te=ds[ds.date>c2]
m=VikaModels(); metrics=m.fit(tr,va,te); m.version='v4.1-safe'; m.save(a.out)
print('TRAIN',len(tr),'VALID',len(va),'TEST',len(te)); print(metrics)
