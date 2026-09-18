from __future__ import annotations
import argparse,json
from pathlib import Path
from vika_engine.training.history_tape import iter_jsonl,normalize_tape
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47
from vika_engine.training.champion_v416 import train_champion

def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.16 Champion live model training')
    ap.add_argument('--history-jsonl',required=True)
    ap.add_argument('--output',default='models/vika_live_v416.joblib')
    ap.add_argument('--report',default='models/vika_live_v416.report.json')
    ap.add_argument('--source',default='livetennis_observed')
    ap.add_argument('--max-snapshots-per-match',type=int,default=80)
    args=ap.parse_args()
    matches=[]
    for raw in iter_jsonl(args.history_jsonl):
        t=normalize_tape(raw,source=args.source)
        if t: matches.append((str(t['match']['id']),t))
    builder=LiveSnapshotBuilderV47(max_snapshots_per_match=args.max_snapshots_per_match)
    snaps=builder.build(matches)
    if not snaps: raise SystemExit('No usable snapshots found')
    report=train_champion(snaps,args.output,args.report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
