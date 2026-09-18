from __future__ import annotations
import math
from collections import Counter
import numpy as np


def clamp(x, lo=.01, hi=.99):
    return max(lo, min(hi, float(x)))


def point_to_game(p: float, rng: np.random.Generator) -> int:
    """Return 1 if server wins the game, 0 otherwise using real tennis scoring."""
    a = b = 0
    while True:
        if rng.random() < p: a += 1
        else: b += 1
        if a >= 4 and a - b >= 2: return 1
        if b >= 4 and b - a >= 2: return 0


def tiebreak(p1: float, p2: float, rng: np.random.Generator) -> int:
    """Seven-point tiebreak with alternating servers. Returns winner side."""
    a = b = 0
    # First point is served by player 1; then 2 points each alternately.
    point_no = 0
    while True:
        block = point_no // 2
        if point_no == 0:
            server = 1
        else:
            server = 2 if block % 2 == 0 else 1
        p = p1 if server == 1 else p2
        if rng.random() < p: a += 1
        else: b += 1
        point_no += 1
        if (a >= 7 or b >= 7) and abs(a-b) >= 2:
            return 1 if a > b else 0


def simulate_set(p1_serve: float, p2_serve: float, p1_return: float, p2_return: float, rng: np.random.Generator, start_server: int = 1):
    """Simulate a full set point-by-point. Returns games and set winner."""
    # p1_serve/p2_serve = probability the named player wins a point on own serve.
    # Opponent return quality is represented implicitly by the other player's serve rate.
    # A conservative mapping turns serve-point strength into point win probability on
    # the opponent's serve instead of assuming the rates are symmetric.
    # Serve-point rates and return-point rates are separate evidence streams.
    # Blend them conservatively when translating them into point probabilities.
    p1_on_own = clamp(.70*p1_serve + .30*(1.0-p2_return))
    p2_on_own = clamp(.70*p2_serve + .30*(1.0-p1_return))
    g1 = g2 = 0
    server = start_server
    while True:
        if server == 1:
            winner = point_to_game(p1_on_own, rng)
        else:
            winner = 0 if point_to_game(p2_on_own, rng) else 1
        if winner == 1: g1 += 1
        else: g2 += 1
        if (g1 >= 6 or g2 >= 6) and abs(g1-g2) >= 2:
            return g1, g2, (1 if g1 > g2 else 0), server
        if g1 == 6 and g2 == 6:
            # tiebreak starts with the player who would serve next in the game rotation.
            tb_w = tiebreak(p1_on_own, p2_on_own, rng)
            return (7,6,tb_w,server) if tb_w else (6,7,tb_w,server)
        server = 2 if server == 1 else 1


def simulate_match(p1_serve: float, p2_serve: float, p1_return: float | None = None, p2_return: float | None = None, *, best_of=3, simulations=20000, seed=42):
    """Point -> game -> set -> match Monte Carlo.

    This is deliberately separate from the live fallback. It is used only when
    point/service evidence exists; otherwise the existing calibrated engine remains
    the source of truth.
    """
    rng = np.random.default_rng(seed)
    p1_return = clamp(1.0-p2_serve) if p1_return is None else clamp(p1_return)
    p2_return = clamp(1.0-p1_serve) if p2_return is None else clamp(p2_return)
    need = 2 if best_of == 3 else 3
    wins = 0
    totals=[]; diffs=[]; sets_counter=Counter(); scores=Counter()
    for _ in range(int(simulations)):
        s1=s2=0; total=diff=0; score=[]; start_server=1
        while s1 < need and s2 < need:
            a,b,w,_ = simulate_set(p1_serve,p2_serve,p1_return,p2_return,rng,start_server)
            total += a+b; diff += a-b; score.append(f'{a}-{b}')
            if w: s1 += 1
            else: s2 += 1
            start_server = 2 if start_server == 1 else 1
        if s1 > s2: wins += 1
        sets_counter[len(score)] += 1
        scores[' '.join(score)] += 1
        totals.append(total); diffs.append(diff)
    n=float(simulations)
    arr=np.asarray(totals); d=np.asarray(diffs)
    return {
        'simulations': int(simulations), 'p1_win': wins/n, 'p2_win': 1-wins/n,
        'expected_total': float(arr.mean()), 'median_total': float(np.median(arr)),
        'expected_diff': float(d.mean()),
        'set_count': {str(k): v/n for k,v in sorted(sets_counter.items())},
        'top_scores': [(k,v/n) for k,v in scores.most_common(10)],
        'over': {str(x): float(np.mean(arr > x)) for x in np.arange(17.5,40.5,1)},
        'handicap': {str(x): float(np.mean(d + x > 0)) for x in np.arange(-8.5,8.6,1)},
    }
