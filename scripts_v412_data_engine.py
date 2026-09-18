from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from vika_engine.features import FeatureBuilder
from vika_engine.data import enrich_targets

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',default='data/archive/all_matches_2015_2025.csv.gz')
    ap.add_argument('--out',default='data/v412_features.csv.gz')
    ap.add_argument('--report',default='models/v412_data_report.json')
    ap.add_argument('--start',default='2015-01-01'); ap.add_argument('--end',default='2025-12-31')
    a=ap.parse_args()
    df=pd.read_csv(a.source,low_memory=False)
    dt=pd.to_datetime(df['tourney_date'].astype(str).str.split('.').str[0],format='%Y%m%d',errors='coerce')
    df=df.loc[(dt>=pd.Timestamp(a.start))&(dt<=pd.Timestamp(a.end))].copy()
    df['tourney_date']=df['tourney_date'].astype(str).str.split('.').str[0]
    df['tour']=df.get('tour','').fillna('').astype(str).str.upper()
    # Keep singles only; archive source is expected to be singles, but enforce it when draw columns exist.
    if 'draw' in df.columns: df=df[df['draw'].astype(str).str.lower().isin(['main','qual','qualifying',''])]
    df=df[df['winner_name'].notna() & df['loser_name'].notna()].copy()
    fb=FeatureBuilder(); ds=fb.build(df)
    ds=ds.sort_values('date').reset_index(drop=True)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); ds.to_csv(a.out,index=False,compression='gzip')
    years=ds['date'].dt.year.value_counts().sort_index().astype(int).to_dict()
    report={'source':a.source,'start':a.start,'end':a.end,'source_matches':int(len(df)),'snapshot_rows':int(len(ds)),'features':int(len([c for c in ds.columns if c not in {'target_win','target_total','target_diff','date','p1_name','p2_name','player1_id','player2_id'}])),'years':{str(k):v for k,v in years.items()},'note':'All features are generated from player state strictly before each match; post-match stats are used only to update state after the snapshot.'}
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
