from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from vika_engine.providers.history import LiveTennisHistoryProvider


def norm(m):
    p = m.get('players') or {}
    p1 = p.get('p1') or {}
    p2 = p.get('p2') or {}
    winner = m.get('winner')
    if winner not in (1, 2):
        return None
    a = p1 if winner == 1 else p2
    b = p2 if winner == 1 else p1
    if not a.get('name') or not b.get('name'):
        return None
    score_obj = m.get('score') or {}
    score = score_obj.get('sets_text') or score_obj.get('text') or m.get('score_text') or ''
    # API detail/list variants sometimes expose a plain string score.
    if not score and isinstance(score_obj, str):
        score = score_obj
    return {
        'tourney_id': m.get('tournament_id') or '',
        'tourney_name': m.get('tournament') or '',
        'surface': str(m.get('surface') or 'Hard').title(),
        'tourney_date': str(m.get('scheduled_time') or m.get('live_at') or m.get('date') or '')[:10].replace('-', ''),
        'match_num': m.get('id') or '',
        'winner_id': a.get('id') or a.get('player_id') or '',
        'winner_name': a.get('name') or '',
        'loser_id': b.get('id') or b.get('player_id') or '',
        'loser_name': b.get('name') or '',
        'winner_rank': a.get('rank'), 'winner_rank_points': a.get('ranking_points'),
        'loser_rank': b.get('rank'), 'loser_rank_points': b.get('ranking_points'),
        'score': score,
        'best_of': 5 if str(m.get('format','')).upper() == 'BO5' else 3,
        'round': m.get('round_code') or m.get('round') or '',
        'minutes': m.get('minutes'),
        'tour': m.get('tour') or '', 'draw': m.get('draw') or '',
        'event_status': m.get('event_status') or '',
        'source': 'livetennisapi_history',
    }


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description='V4.22 refresh: current 2023+ results from official Live Tennis API')
    ap.add_argument('--start', default='2026-01-01')
    ap.add_argument('--end', default=str(date.today()))
    ap.add_argument('--tour', choices=['atp','wta'])
    ap.add_argument('--out', default='data/live_results_2023_now.csv.gz')
    args = ap.parse_args()
    p = LiveTennisHistoryProvider()
    if not p.available:
        raise SystemExit('LIVETENNISAPI_KEY is required')
    rows=[]; seen=set()
    for m in p.iter_history_matches(args.start, args.end, args.tour):
        if str(m.get('draw') or '').lower() not in ('singles',''):
            continue
        if m.get('status') not in (None, 'completed'):
            continue
        r=norm(m)
        if not r: continue
        key=str(r['match_num']) or f"{r['tourney_date']}|{r['winner_name']}|{r['loser_name']}"
        if key in seen: continue
        seen.add(key); rows.append(r)
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out,index=False,compression='gzip')
    print(json.dumps({'rows':len(rows),'start':args.start,'end':args.end,'tour':args.tour,'out':str(out)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
