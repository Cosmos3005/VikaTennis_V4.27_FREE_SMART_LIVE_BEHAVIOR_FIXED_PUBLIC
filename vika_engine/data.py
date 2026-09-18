from __future__ import annotations

import math
import re
from pathlib import Path
import time

import pandas as pd
import requests


def download_years(tour, start, end, out_dir='data/raw', source='huggingface'):
    """Download Sackmann-format yearly results. Intended for research/non-commercial use."""
    raw_dir = Path(out_dir) / tour
    raw_dir.mkdir(parents=True, exist_ok=True)
    base = 'https://huggingface.co/datasets/Aneeshers/tennis-sackmann-archive/resolve/main'
    for year in range(int(start), int(end) + 1):
        name = f'{tour}_matches_{year}.csv'
        url = f'{base}/{tour}/{name}'
        target = raw_dir / name
        if target.exists() and target.stat().st_size > 1000:
            continue
        print(f'[download] {url}')
        r = requests.get(url, timeout=60)
        if r.status_code == 404:
            print(f'[skip] {year}: not found')
            continue
        r.raise_for_status()
        target.write_bytes(r.content)
        print(f'[ok] {year}: {target.stat().st_size:,} bytes')
        time.sleep(.25)


def load_raw(tour, out_dir='data/raw'):
    raw_dir = Path(out_dir) / tour
    files = sorted(raw_dir.glob('*.csv'))
    if not files:
        raise FileNotFoundError(f'No raw {tour} files in {raw_dir}')
    dfs = []
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        df['tour'] = tour
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def _score_outcome(score: str):
    s = str(score or '').strip().upper()
    if not s or s in {'W/O', 'WO', 'WALKOVER', 'DEFAULT', 'DEF', 'ABN', 'ABD'}:
        return 'incomplete'
    if 'RET' in s:
        return 'retired'
    if 'DEF' in s or 'W/O' in s or 'WO' in s:
        return 'incomplete'
    return 'completed'


def parse_score(score):
    """Return total games, game differential and legal completed-match flag."""
    outcome = _score_outcome(score)
    if outcome != 'completed':
        return 0, 0, False, outcome
    total = diff = 0
    valid_sets = 0
    for token in str(score).split():
        token = re.sub(r'\([^)]*\)', '', token)
        if '-' not in token:
            continue
        try:
            a, b = token.split('-')[:2]
            a, b = int(a), int(b)
        except (TypeError, ValueError):
            continue
        # A normal tennis set must have at least six games and cannot be 6-6
        # after stripping a tiebreak marker.  This removes obvious malformed rows.
        if a < 0 or b < 0 or (max(a, b) < 6) or (a == b):
            continue
        total += a + b
        diff += a - b
        valid_sets += 1
    return total, diff, valid_sets > 0, outcome


def enrich_targets(df):
    df = df.copy()
    parsed = df['score'].apply(parse_score)
    df['total_games'] = parsed.map(lambda x: x[0]).astype(float)
    df['games_diff'] = parsed.map(lambda x: x[1]).astype(float)
    df['valid_target'] = parsed.map(lambda x: x[2]).astype(bool)
    df['match_outcome'] = parsed.map(lambda x: x[3])
    return df
