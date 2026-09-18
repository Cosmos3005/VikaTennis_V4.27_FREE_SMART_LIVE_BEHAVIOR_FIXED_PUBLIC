from __future__ import annotations
import argparse, json
from scripts_v47_train_live import load_jsonl
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47
from vika_engine.training.champion_live import evaluate_champion

def main():
    ap=argparse.ArgumentParser(description='VikaTennis Champion Backtest over historical live tapes')
    ap.add_argument('--history-jsonl',required=True)
    ap.add_argument('--model',default='models/vika_live_v48.joblib')
    ap.add_argument('--output',default='models/champion_backtest_v49.json')
    ap.add_argument('--max-snapshots-per-match',type=int,default=80)
    args=ap.parse_args()
    matches=load_jsonl(args.history_jsonl)
    builder=LiveSnapshotBuilderV47(max_snapshots_per_match=args.max_snapshots_per_match,prior_provider=None)
    snaps=builder.build(matches)
    if len(snaps)<100: raise SystemExit(f'Not enough snapshots: {len(snaps)}')
    # This report is intentionally run on a supplied holdout dataset. Training
    # and test split are handled by the V4.7 trainer; do not use this report on
    # the same data used to fit the model for promotion.
    report=evaluate_champion(args.model,snaps,args.output)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
