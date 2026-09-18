from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import deque
import math
from typing import Any


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def _num(d: Any, *names, default=0.0) -> float:
    if isinstance(d, dict):
        for n in names:
            if d.get(n) is not None:
                try: return float(d[n])
                except Exception: pass
    else:
        for n in names:
            v = getattr(d, n, None)
            if v is not None:
                try: return float(v)
                except Exception: pass
    return float(default)


@dataclass
class MomentumSnapshot:
    ewma: float
    window_score: float
    pressure: float
    serve_edge: float
    return_edge: float
    break_edge: float
    sample_size: int


class PointMomentum:
    """Online, leakage-safe momentum accumulator for played points.

    Each point is converted to a signed outcome (+1 P1, -1 P2). EWMA gives
    recent points more weight. Context features are deliberately bounded so a
    short streak cannot overpower the pre-match prior by itself.
    """
    def __init__(self, alpha: float = 0.18, window: int = 25):
        self.alpha = float(alpha)
        self.window = int(window)
        self.ewma = 0.0
        self.points: deque[float] = deque(maxlen=window)
        self.p1_service_points = 0
        self.p2_service_points = 0
        self.p1_return_points = 0
        self.p2_return_points = 0
        self.p1_break_points = 0
        self.p2_break_points = 0
        self.p1_break_won = 0
        self.p2_break_won = 0

    def update(self, event: Any) -> MomentumSnapshot:
        winner = _num(event, "winner", "winner_player", "point_winner", "pointWinner", default=0)
        if winner not in (1, 2):
            # Some feeds use player_id strings; explicit winner_index is preferred.
            winner = _num(event, "winner_index", "winnerIndex", default=0)
        signed = 1.0 if winner == 1 else -1.0 if winner == 2 else 0.0
        if signed:
            self.ewma = self.alpha * signed + (1.0 - self.alpha) * self.ewma
            self.points.append(signed)

        server = int(_num(event, "server", "server_index", "serving_player", default=0))
        if signed and server in (1, 2):
            if server == 1:
                self.p1_service_points += 1
                if winner == 1: self.p1_service_points += 0
                else: self.p1_return_points += 1
            else:
                self.p2_service_points += 1
                if winner == 2: self.p2_service_points += 0
                else: self.p2_return_points += 1

        bp = bool(event.get("break_point", False)) if isinstance(event, dict) else bool(getattr(event, "break_point", False))
        if bp and server in (1, 2):
            if server == 1:
                self.p1_break_points += 1
                if winner == 2: self.p2_break_won += 1
            else:
                self.p2_break_points += 1
                if winner == 1: self.p1_break_won += 1

        return self.snapshot()

    def snapshot(self) -> MomentumSnapshot:
        w = list(self.points)
        window_score = sum(w) / len(w) if w else 0.0
        pressure = _clamp(self.ewma * 0.65 + window_score * 0.35)
        service_total = self.p1_service_points + self.p2_service_points
        return MomentumSnapshot(
            ewma=round(_clamp(self.ewma), 6),
            window_score=round(_clamp(window_score), 6),
            pressure=round(pressure, 6),
            serve_edge=round(_clamp((self.p1_service_points - self.p2_service_points) / max(1, service_total)), 6),
            return_edge=round(_clamp((self.p1_return_points - self.p2_return_points) / max(1, self.p1_return_points + self.p2_return_points)), 6),
            break_edge=round(_clamp((self.p1_break_won - self.p2_break_won) / max(1, self.p1_break_points + self.p2_break_points)), 6),
            sample_size=len(self.points),
        )

    def to_dict(self):
        return asdict(self.snapshot())
