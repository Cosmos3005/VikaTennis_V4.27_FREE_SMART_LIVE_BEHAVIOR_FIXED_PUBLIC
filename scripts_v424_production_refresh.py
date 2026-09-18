from __future__ import annotations
import argparse, gzip, json, os, shutil, subprocess, sys
from datetime import date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from vika_engine.providers.history import LiveTennisHistoryProvider
from vika_engine.point_features import extract_match_point_stats

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; MODELS=ROOT/'models'; PBP=DATA/'pbp'

def run_script(name,*args):
    # Supports both script paths and Python module flags (e.g. -m pytest).
    if str(name).startswith('-'):
        cmd=[sys.executable,str(name),*map(str,args)]
    else:
        cmd=[sys.executable,str(ROOT/name),*map(str,args)]
    print('\n>>>',' '.join(cmd))
    p=subprocess.run(cmd,cwd=ROOT)
    if p.returncode: raise SystemExit(p.returncode)

def backup(path:Path):
    if path.exists():
        b=path.with_suffix(path.suffix+'.bak')
        shutil.copy2(path,b)

def load_pbp_stats(path):
    if not path.exists(): return []
    out=[]
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            try:
                obj=json.loads(line); stat=extract_match_point_stats(obj.get('tape') or {})
                if stat:
                    stat['match_id']=str(obj.get('match_id'))
                    out.append(stat)
            except Exception: continue
    return out

def main():
    load_dotenv(ROOT/'.env')
    ap=argparse.ArgumentParser(description='Vika V4.24 production refresh: results + qualified PBP + state + model + audit')
    ap.add_argument('--start',default='2026-01-01'); ap.add_argument('--end',default=str(date.today()))
    ap.add_argument('--tour',choices=['atp','wta']); ap.add_argument('--pbp-limit',type=int,default=300)
    ap.add_argument('--skip-pbp',action='store_true'); ap.add_argument('--full-state',action='store_true')
    a=ap.parse_args()
    if not os.getenv('LIVETENNISAPI_KEY'): raise SystemExit('LIVETENNISAPI_KEY is missing in local .env')
    MODELS.mkdir(exist_ok=True); PBP.mkdir(parents=True,exist_ok=True)
    for p in [DATA/'live_results_2023_now.csv.gz',MODELS/'player_state_v422.json',MODELS/'vika_models_v422.joblib']:
        backup(p)
    refresh_log=MODELS/'v424_refresh_result.json'
    run_script('scripts_v422_refresh.py','--start',a.start,'--end',a.end,*(['--tour',a.tour] if a.tour else []))
    pbp_path=PBP/'history_tapes.jsonl.gz'
    provider=LiveTennisHistoryProvider()
    qualified=[]
    if not a.skip_pbp:
        # One history-list request can qualify many matches; tape requests are then capped.
        for m in provider.iter_history_matches(a.start,a.end,a.tour):
            tape=m.get('tape') or {}
            cov=str(tape.get('coverage','')).lower()
            src=str(tape.get('point_source','')).lower()
            if cov in ('none','') or src=='game': continue
            mid=m.get('id')
            if mid is not None: qualified.append(str(mid))
            if len(qualified)>=a.pbp_limit: break
        # Reuse existing downloader so deduplication and honest coverage remain centralized.
        if qualified:
            run_script('scripts_v422_tape_download.py','--match-ids',','.join(qualified),'--out',str(pbp_path))
    stats=load_pbp_stats(pbp_path)
    if stats:
        pd.DataFrame(stats).to_csv(PBP/'point_match_stats.csv',index=False)

    # Incremental state update is the default; full rebuild is opt-in.
    run_script('scripts_v422_rebuild_state.py',*(['--full'] if a.full_state else []))
    run_script('scripts_v422_train.py')
    run_script('-m','pytest','-q')

    # Build one compact report that the director can send back for analysis.
    def read_json(path):
        try:
            return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else {}
        except Exception:
            return {}
    results_path=DATA/'live_results_2023_now.csv.gz'
    results_rows=0
    results_min=results_max=None
    tours={}; surfaces={}
    if results_path.exists():
        rdf=pd.read_csv(results_path,low_memory=False)
        results_rows=len(rdf)
        if 'tourney_date' in rdf.columns:
            ds=pd.to_datetime(rdf['tourney_date'].astype(str).str[:8],format='%Y%m%d',errors='coerce')
            if ds.notna().any(): results_min=str(ds.min().date()); results_max=str(ds.max().date())
        if 'tour' in rdf.columns: tours={str(k):int(v) for k,v in rdf['tour'].fillna('').value_counts().to_dict().items()}
        if 'surface' in rdf.columns: surfaces={str(k):int(v) for k,v in rdf['surface'].fillna('').value_counts().to_dict().items()}
    state_report=read_json(MODELS/'v422_state_report.json')
    train_report=read_json(MODELS/'v422_training_report.json')
    report={
        'status':'ok','version':'v4.24','generated_at':__import__('datetime').datetime.now().isoformat(timespec='seconds'),
        'period':{'start':a.start,'end':a.end},
        'results':{'rows':results_rows,'min_date':results_min,'max_date':results_max,'tours':tours,'surfaces':surfaces,'file':str(results_path.relative_to(ROOT))},
        'pbp':{'qualified_requested':len(qualified),'stats_rows':len(stats),'file':str((PBP/'point_match_stats.csv').relative_to(ROOT)) if (PBP/'point_match_stats.csv').exists() else None,'tape_file':str(pbp_path.relative_to(ROOT)) if pbp_path.exists() else None},
        'state':state_report,
        'model':train_report,
        'tests':{'command':'python -m pytest -q','status':'PASS'},
        'artifacts':{'state':'models/player_state_v422.json','model':'models/vika_models_v422.joblib'}
    }
    (MODELS/'v424_production_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
