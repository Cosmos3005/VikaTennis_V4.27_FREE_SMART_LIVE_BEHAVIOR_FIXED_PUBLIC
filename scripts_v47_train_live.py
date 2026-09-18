from __future__ import annotations
import argparse, json, os
from pathlib import Path
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47, train_live_model
from vika_engine.providers.history import LiveTennisHistoryProvider


def load_jsonl(path):
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                obj=json.loads(line)
                yield str(obj.get('match_id') or obj.get('id') or obj.get('match',{}).get('id') or 'unknown'), obj.get('tape',obj)

def fetch_ids(ids, complete=False):
    p=LiveTennisHistoryProvider()
    if not p.available: raise SystemExit('LIVETENNISAPI_KEY is required for --match-ids')
    for mid in ids:
        yield str(mid),p.history_tape(mid,complete=complete)

def prior_provider_factory():
    try:
        from vika_engine.prediction import PredictionEngine
        e=PredictionEngine()
        def prior(a,b):
            try:return float(e.predict(a,b,'Hard',3,simulations=1000)['p1_win'])
            except Exception:return .5
        return prior
    except Exception:
        return lambda a,b:.5

def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.7 historical live XGBoost trainer')
    ap.add_argument('--history-jsonl', help='JSONL with one HistoryTape envelope per line')
    ap.add_argument('--match-ids', nargs='*', help='Live Tennis API historical match IDs')
    ap.add_argument('--complete', action='store_true', help='request complete point tape from API')
    ap.add_argument('--output', default='models/vika_live_v47.joblib')
    ap.add_argument('--max-snapshots-per-match', type=int, default=250)
    args=ap.parse_args()
    if not args.history_jsonl and not args.match_ids: ap.error('Provide --history-jsonl or --match-ids')
    matches=load_jsonl(args.history_jsonl) if args.history_jsonl else fetch_ids(args.match_ids,args.complete)
    builder=LiveSnapshotBuilderV47(max_snapshots_per_match=args.max_snapshots_per_match,prior_provider=prior_provider_factory())
    snaps=builder.build(matches)
    model,metrics=train_live_model(snaps,args.output)
    report=Path(args.output).with_suffix('.report.json'); report.write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
    print(f'\nMODEL: {args.output}\nREPORT: {report}')

if __name__=='__main__': main()
