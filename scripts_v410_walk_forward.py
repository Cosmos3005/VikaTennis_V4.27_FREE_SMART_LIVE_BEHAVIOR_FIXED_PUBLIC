from __future__ import annotations
import argparse,json
from pathlib import Path
from vika_engine.training.walk_forward_live import run_from_jsonl,run_walk_forward,aggregate

def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.10 expanding-window walk-forward live backtest')
    ap.add_argument('--history-jsonl',required=True);ap.add_argument('--output',default='models/walk_forward_v410.json');ap.add_argument('--max-snapshots-per-match',type=int,default=80);ap.add_argument('--validation-days',type=int,default=120)
    a=ap.parse_args();snaps=run_from_jsonl(a.history_jsonl,a.max_snapshots_per_match)
    if len({s.match_id for s in snaps})<100:raise SystemExit('Need at least 100 matches')
    r=aggregate(run_walk_forward(snaps,a.validation_days));r.update({'history_jsonl':a.history_jsonl,'max_snapshots_per_match':a.max_snapshots_per_match,'validation_days':a.validation_days});Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
