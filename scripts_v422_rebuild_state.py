from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from vika_engine.data import enrich_targets
from vika_engine.ratings.player_state import PlayerStateStore


def load_any(path):
    return pd.read_csv(path, low_memory=False)


def normalize(df):
    df=enrich_targets(df.copy())
    df=df[df.valid_target].copy()
    df['__date']=pd.to_datetime(df['tourney_date'].astype(str).str[:8],format='%Y%m%d',errors='coerce')
    return df.dropna(subset=['__date']).sort_values(['__date','match_num'] if 'match_num' in df.columns else ['__date']).drop(columns='__date')


def main():
    ap=argparse.ArgumentParser(description='V4.22 incremental leakage-safe Player State rebuild')
    ap.add_argument('--base',default='data/all_matches_2015_2025.csv.gz')
    ap.add_argument('--extra',default='data/live_results_2023_now.csv.gz')
    ap.add_argument('--state',default='models/player_state_v414.json')
    ap.add_argument('--out',default='models/player_state_v422.json')
    ap.add_argument('--full',action='store_true',help='rebuild from the full archive; slower')
    a=ap.parse_args()
    extra=normalize(load_any(a.extra)) if Path(a.extra).exists() else pd.DataFrame()
    if not len(extra):
        if not Path(a.state).exists(): raise SystemExit('No refreshed results and no existing state')
        st=PlayerStateStore.load(a.state); st.save(a.out)
        print(json.dumps({'mode':'copy','rows':0,'players':len(st.players),'max_date':str(st.max_date),'out':a.out},ensure_ascii=False,indent=2)); return
    if not a.full and Path(a.state).exists():
        st=PlayerStateStore.load(a.state)
        cutoff=pd.Timestamp(st.max_date) if st.max_date is not None else pd.Timestamp('1900-01-01')
        extra=extra[extra['tourney_date'].astype(str).str[:8].map(lambda x: pd.to_datetime(x,format='%Y%m%d',errors='coerce'))>cutoff]
        st.ingest(extra); mode='incremental'
    else:
        base=normalize(load_any(a.base))
        if 'match_num' in base.columns and 'match_num' in extra.columns:
            extra=extra[~extra.set_index(['tourney_date','winner_name','loser_name','match_num']).index.isin(base.set_index(['tourney_date','winner_name','loser_name','match_num']).index)]
        st=PlayerStateStore(); st.ingest(pd.concat([base,extra],ignore_index=True)); mode='full'
    st.save(a.out)
    report={'mode':mode,'rows_applied':int(len(extra)),'players':len(st.players),'max_date':str(st.max_date),'out':a.out}
    Path('models/v422_state_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
