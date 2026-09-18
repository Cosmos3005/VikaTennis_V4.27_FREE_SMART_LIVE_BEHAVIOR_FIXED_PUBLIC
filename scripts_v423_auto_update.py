from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

def run(cmd):
    print('\n>>>', ' '.join(map(str, cmd)))
    p = subprocess.run([sys.executable, *cmd], cwd=ROOT)
    if p.returncode:
        raise SystemExit(p.returncode)

def main():
    load_dotenv(ROOT / '.env')
    ap = argparse.ArgumentParser(description='Vika Tennis V4.23 one-command data refresh + state + training')
    ap.add_argument('--start', default='2026-01-01')
    ap.add_argument('--end', default=str(date.today()))
    ap.add_argument('--tour', choices=['atp','wta'], default=None)
    ap.add_argument('--full-state', action='store_true')
    ap.add_argument('--skip-train', action='store_true')
    ap.add_argument('--skip-tests', action='store_true')
    a = ap.parse_args()
    if not os.getenv('LIVETENNISAPI_KEY'):
        raise SystemExit('LIVETENNISAPI_KEY is missing. Put your private key in .env; never paste it into chat.')
    cmd=['scripts_v422_refresh.py','--start',a.start,'--end',a.end]
    if a.tour: cmd += ['--tour',a.tour]
    run(cmd)
    state=['scripts_v422_rebuild_state.py']
    if a.full_state: state += ['--full']
    run(state)
    if not a.skip_train:
        run(['scripts_v422_train.py'])
    if not a.skip_tests:
        run(['-m','pytest','-q','tests/test_v422.py','tests/test_v421.py'])
    report={
        'status':'ok','version':'v4.23','start':a.start,'end':a.end,
        'data':'data/live_results_2023_now.csv.gz',
        'state':'models/player_state_v422.json',
        'model':'models/vika_models_v422.joblib'
    }
    Path('models/v423_refresh_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
