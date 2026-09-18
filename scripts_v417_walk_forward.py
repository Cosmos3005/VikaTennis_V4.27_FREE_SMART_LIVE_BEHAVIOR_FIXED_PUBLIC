from __future__ import annotations
import argparse,json
from vika_engine.training.history_tape import iter_jsonl,normalize_tape
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47
from vika_engine.training.walk_forward_v417 import run_walk_forward

def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.17 chronological walk-forward live champion evaluation')
    ap.add_argument('--history-jsonl',required=True)
    ap.add_argument('--report',default='models/vika_live_v417.walkforward.json')
    ap.add_argument('--source',default='livetennis_observed')
    ap.add_argument('--max-snapshots-per-match',type=int,default=80)
    args=ap.parse_args()
    matches=[]; seen=set()
    for raw in iter_jsonl(args.history_jsonl):
        t=normalize_tape(raw,source=args.source)
        if t and t['match']['id'] not in seen:
            seen.add(t['match']['id']); matches.append((str(t['match']['id']),t))
    snaps=LiveSnapshotBuilderV47(max_snapshots_per_match=args.max_snapshots_per_match).build(matches)
    if not snaps: raise SystemExit('No usable snapshots found')
    report=run_walk_forward(snaps)
    from pathlib import Path
    Path(args.report).parent.mkdir(parents=True,exist_ok=True)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
