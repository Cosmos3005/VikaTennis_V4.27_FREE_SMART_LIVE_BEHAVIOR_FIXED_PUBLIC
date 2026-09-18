from __future__ import annotations
import argparse, json
from vika_engine.engine import PredictionEngine
from vika_engine.providers.history import LiveTennisHistoryProvider
from vika_engine.training.live_backtest import LiveHistoricalBacktester


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('match_ids', nargs='+')
    ap.add_argument('--complete', action='store_true')
    ap.add_argument('--output', default='models/live_backtest_v46.json')
    args=ap.parse_args()
    provider=LiveTennisHistoryProvider()
    if not provider.available: raise SystemExit('LIVETENNISAPI_KEY is required')
    engine=PredictionEngine()
    bt=LiveHistoricalBacktester(engine)
    tapes=[]
    for mid in args.match_ids:
        tapes.append((mid, provider.history_tape(mid, complete=args.complete)))
    report=bt.run(tapes)
    with open(args.output,'w',encoding='utf-8') as f: json.dump(report.__dict__,f,ensure_ascii=False,indent=2)
    print(json.dumps(report.__dict__,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
