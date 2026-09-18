from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import date
from vika_engine.training.history_tape import iter_jsonl, normalize_tape, write_jsonl
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47


def load_tapes(paths, source):
    seen=set(); out=[]
    for p in paths:
        for raw in iter_jsonl(p):
            t=normalize_tape(raw,source=source)
            if not t: continue
            mid=t['match']['id']
            if mid in seen: continue
            seen.add(mid); out.append(t)
    return out


def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.15 point-by-point causal data engine')
    ap.add_argument('--input',action='append',required=True,help='JSONL/JSONL.GZ tape source; repeatable')
    ap.add_argument('--source',default='unknown',choices=['livetennis_observed','livetennis_reconstructed','sackmann_public','unknown'])
    ap.add_argument('--snapshots-out',default='data/live_snapshots_v415.jsonl')
    ap.add_argument('--checkpoint-every',type=int,default=1)
    ap.add_argument('--max-snapshots-per-match',type=int,default=80)
    ap.add_argument('--min-points',type=int,default=10)
    a=ap.parse_args()
    tapes=load_tapes(a.input,a.source)
    tapes=[t for t in tapes if len(t['tape'])>=a.min_points]
    builder=LiveSnapshotBuilderV47(checkpoint_every=a.checkpoint_every,max_snapshots_per_match=a.max_snapshots_per_match)
    snaps=builder.build([(t['match']['id'],t) for t in tapes])
    Path(a.snapshots_out).parent.mkdir(parents=True,exist_ok=True)
    with open(a.snapshots_out,'w',encoding='utf-8') as f:
        for s in snaps:
            f.write(json.dumps({'match_id':s.match_id,'date':s.date,'seq':s.seq,'target':s.target,'coverage':s.coverage,'features':s.features},ensure_ascii=False,separators=(',',':'))+'\n')
    by_source={}
    for t in tapes: by_source[t['meta'].get('point_source','unknown')]=by_source.get(t['meta'].get('point_source','unknown'),0)+1
    print(json.dumps({'matches':len(tapes),'snapshots':len(snaps),'source_breakdown':by_source,'out':a.snapshots_out},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
