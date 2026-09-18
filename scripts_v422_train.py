from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from vika_engine.data import enrich_targets
from vika_engine.features import FeatureBuilder
from vika_engine.models import VikaModels


def main():
    ap=argparse.ArgumentParser(description='V4.22 chronological training after data refresh')
    ap.add_argument('--base',default='data/all_matches_2015_2025.csv.gz')
    ap.add_argument('--extra',default='data/live_results_2023_now.csv.gz')
    ap.add_argument('--out',default='models/vika_models_v422.joblib')
    args=ap.parse_args()
    base=pd.read_csv(args.base,low_memory=False)
    extra=pd.read_csv(args.extra,low_memory=False) if Path(args.extra).exists() else pd.DataFrame()
    if len(extra):
        for c in base.columns:
            if c not in extra.columns: extra[c]=None
        extra=extra[base.columns]
    df=pd.concat([base,extra],ignore_index=True) if len(extra) else base
    df=enrich_targets(df); df=df[df.valid_target].copy()
    if 'match_num' in df.columns:
        df=df.drop_duplicates(subset=['tourney_date','winner_name','loser_name','match_num'])
    ds=FeatureBuilder().build(df)
    ds=ds.sort_values('date').reset_index(drop=True)
    dates=sorted(ds.date.dropna().unique())
    if len(dates)<60: raise SystemExit('Need at least 60 distinct dates')
    # Strict chronological train/validation/test. No random split.
    c1=dates[int(len(dates)*.70)]; c2=dates[int(len(dates)*.85)]
    train=ds[ds.date<=c1]; valid=ds[(ds.date>c1)&(ds.date<=c2)]; test=ds[ds.date>c2]
    model=VikaModels(); metrics=model.fit(train,valid,test); model.version='v4.22'
    model.save(args.out)
    report={'version':'v4.22','rows':len(ds),'features':len(model.feature_columns),'train':len(train),'valid':len(valid),'test':len(test),'train_end':str(c1),'valid_end':str(c2),'test_start':str(min(test.date)),'metrics':metrics}
    Path('models/v422_training_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
