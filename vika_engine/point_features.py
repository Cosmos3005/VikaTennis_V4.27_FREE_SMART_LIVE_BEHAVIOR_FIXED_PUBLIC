from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path


def _rows(tape_obj):
    rows = tape_obj.get('tape') if isinstance(tape_obj, dict) else None
    return rows if isinstance(rows, list) else []


def extract_match_point_stats(tape_obj):
    """Extract honest point/server stats from a Live Tennis HistoryTape.

    The API's `server` field is the server for the NEXT point, so attribution uses
    the previous row's server and the current row's point winner. No point is guessed.
    """
    rows = _rows(tape_obj)
    if len(rows) < 2:
        return None
    meta = tape_obj.get('meta') or {}
    if str(meta.get('coverage', '')).lower() in {'none'}:
        return None
    match = tape_obj.get('match') or {}
    players = match.get('players') or {}
    p1 = (players.get('p1') or {}).get('name') or match.get('p1_name')
    p2 = (players.get('p2') or {}).get('name') or match.get('p2_name')
    if not p1 or not p2:
        # Archive tape is winner-first.
        w = match.get('winner') or {}
        l = match.get('loser') or {}
        p1 = w.get('name') if isinstance(w, dict) else None
        p2 = l.get('name') if isinstance(l, dict) else None
    if not p1 or not p2:
        return None

    points = [0, 0]
    won = [0, 0]
    service_points = [0, 0]
    service_won = [0, 0]
    return_points = [0, 0]
    return_won = [0, 0]
    attributable = 0
    for i in range(1, len(rows)):
        prev = rows[i - 1] or {}
        cur = rows[i] or {}
        server = prev.get('server')
        winner = cur.get('winner', cur.get('point_winner'))
        if server not in (1, 2) or winner not in (1, 2):
            continue
        s = int(server) - 1
        w = int(winner) - 1
        attributable += 1
        points[w] += 1
        won[w] += 1
        service_points[s] += 1
        service_won[s] += int(w == s)
        r = 1 - s
        return_points[r] += 1
        return_won[r] += int(w == r)

    if attributable < 20:
        return None
    return {
        'p1_name': p1,
        'p2_name': p2,
        'points': points,
        'service_points': service_points,
        'service_won': service_won,
        'return_points': return_points,
        'return_won': return_won,
        'attributable_points': attributable,
        'coverage': meta.get('coverage'),
        'basis': meta.get('basis') or meta.get('point_source'),
    }


def aggregate_player_point_stats(tapes):
    """Build cumulative player point stats from tape objects in chronological order."""
    out = defaultdict(lambda: {'service_points': 0, 'service_won': 0, 'return_points': 0, 'return_won': 0, 'matches': 0, 'points': 0})
    for obj in tapes:
        stat = extract_match_point_stats(obj)
        if not stat:
            continue
        names = [stat['p1_name'], stat['p2_name']]
        for i, name in enumerate(names):
            s = out[name]
            s['service_points'] += stat['service_points'][i]
            s['service_won'] += stat['service_won'][i]
            s['return_points'] += stat['return_points'][i]
            s['return_won'] += stat['return_won'][i]
            s['points'] += stat['attributable_points']
            s['matches'] += 1
    return dict(out)


def iter_jsonl(path):
    opener = __import__('gzip').open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
