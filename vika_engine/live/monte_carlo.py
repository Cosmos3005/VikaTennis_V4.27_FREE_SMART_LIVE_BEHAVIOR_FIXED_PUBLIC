from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math
import numpy as np


def _clamp(x, lo=.01, hi=.99):
    return max(lo, min(hi, float(x)))


def _score_pair(v, default=(0, 0)):
    if isinstance(v, dict):
        return int(v.get('p1', v.get('player1', default[0])) or 0), int(v.get('p2', v.get('player2', default[1])) or 0)
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        def n(x):
            try: return int(x)
            except Exception: return 0
        return n(v[0]), n(v[1])
    return default


@dataclass
class LiveMCResult:
    simulations: int
    p1_win: float
    p2_win: float
    p1_set_next: float
    p2_set_next: float
    p1_two_zero: float
    p2_two_zero: float
    expected_remaining_sets: float
    expected_remaining_games: float


class LiveMonteCarlo:
    """Simulate only the remainder of a live match.

    The pre-match probability is the prior. Live score and observed stats adjust
    game-level probabilities; Monte Carlo then resolves the remaining sets.
    It never invents point events when the provider only exposes game coverage.
    """
    def __init__(self, seed: int = 20260908):
        self.rng = np.random.default_rng(seed)

    @staticmethod
    def _game_probability(prior: float, f: Any, p1: float) -> tuple[float, float]:
        # Start from prior, then use observed service/return performance when enough
        # observations exist. This is deliberately conservative: live evidence is
        # shrunk toward the pre-match prior to avoid overreaction to tiny samples.
        p = float(prior)
        sp1 = float(getattr(f, 'p1_service_points_won', 0) or 0)
        sp2 = float(getattr(f, 'p2_service_points_won', 0) or 0)
        rp1 = float(getattr(f, 'p1_return_points_won', 0) or 0)
        rp2 = float(getattr(f, 'p2_return_points_won', 0) or 0)
        evidence = []
        if sp1 + sp2 >= 20:
            evidence.append((sp1 - sp2) / max(20.0, sp1 + sp2) * .55)
        if rp1 + rp2 >= 20:
            evidence.append((rp1 - rp2) / max(20.0, rp1 + rp2) * .45)
        bp = float(getattr(f, 'p1_break_points', 0) or 0) + float(getattr(f, 'p2_break_points', 0) or 0)
        bpw = float(getattr(f, 'p1_break_points_won', 0) or 0) - float(getattr(f, 'p2_break_points_won', 0) or 0)
        if bp >= 4:
            evidence.append(.08 * bpw / max(1.0, bp))
        edge = sum(evidence)
        # Convert match prior into a neutral per-game prior and apply small live edge.
        neutral_game = .5 + (p - .5) * .28
        game_p1 = _clamp(neutral_game + edge * .28)
        if p1 >= .5:
            game_p1 = _clamp(game_p1 + (p1 - p) * .10)
        return game_p1, 1.0 - game_p1

    def _simulate_set_from_score(self, g1: int, g2: int, p_game: float):
        while True:
            if g1 >= 6 or g2 >= 6:
                if abs(g1 - g2) >= 2:
                    return g1, g2
                if g1 == 6 and g2 == 6:
                    tb_p = _clamp(.5 + (p_game - .5) * 1.65, .05, .95)
                    return (7, 6) if self.rng.random() < tb_p else (6, 7)
            if self.rng.random() < p_game:
                g1 += 1
            else:
                g2 += 1

    def simulate(self, *, prior: float, live_features: Any, momentum_pressure: float = 0.0,
                 simulations: int = 100000, best_of: int = 3) -> dict:
        sets1 = int(getattr(live_features, 'p1_sets', 0))
        sets2 = int(getattr(live_features, 'p2_sets', 0))
        games1 = int(getattr(live_features, 'p1_games', 0))
        games2 = int(getattr(live_features, 'p2_games', 0))
        p1_live = _clamp(prior + .16 * momentum_pressure)
        base_game, _ = self._game_probability(prior, live_features, p1_live)
        # Score itself is already incorporated by starting from the current game/set state.
        # Momentum only gets a modest extra game-level effect.
        p_game = _clamp(base_game + .10 * momentum_pressure)
        to_win = 2 if best_of == 3 else 3
        p1wins = next_set_p1 = p2wins = two_zero_1 = two_zero_2 = 0
        rem_sets = rem_games = 0.0
        for _ in range(int(simulations)):
            s1, s2 = sets1, sets2
            g1, g2 = games1, games2
            sets_played = 0
            games_played = 0
            first_set_p1 = None
            while s1 < to_win and s2 < to_win:
                a, b = self._simulate_set_from_score(g1, g2, p_game)
                games_played += max(0, a-g1) + max(0, b-g2)
                # Current score can already be complete; count a set only when it resolves.
                if a > b: s1 += 1
                else: s2 += 1
                if first_set_p1 is None:
                    first_set_p1 = a > b
                g1 = g2 = 0
                sets_played += 1
            if s1 > s2:
                p1wins += 1
                if sets1 == 0 and sets2 == 0 and s1 == 2 and s2 == 0:
                    two_zero_1 += 1
            else:
                p2wins += 1
                if sets1 == 0 and sets2 == 0 and s2 == 2 and s1 == 0:
                    two_zero_2 += 1
            next_set_p1 += int(first_set_p1 is True)
            rem_sets += sets_played
            rem_games += games_played
        n = float(simulations)
        return {
            'simulations': int(simulations),
            'p1_win': p1wins / n,
            'p2_win': p2wins / n,
            'p1_set_next': next_set_p1 / n,
            'p2_set_next': 1 - next_set_p1 / n,
            'p1_two_zero': two_zero_1 / n,
            'p2_two_zero': two_zero_2 / n,
            'expected_remaining_sets': rem_sets / n,
            'expected_remaining_games': rem_games / n,
            'game_probability_p1': p_game,
        }
