from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Optional
import math
import statistics


def _get(x: Any, *names, default=None):
    if isinstance(x, dict):
        for n in names:
            if n in x and x[n] is not None:
                return x[n]
    else:
        for n in names:
            if hasattr(x, n):
                v = getattr(x, n)
                if v is not None:
                    return v
    return default


def _num(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _name(obj, side: int):
    p = _get(obj, 'p1' if side == 1 else 'p2', 'player1' if side == 1 else 'player2', default=None)
    if isinstance(p, dict):
        return p.get('name') or p.get('full_name') or p.get('player_name')
    return _get(p, 'name', 'full_name', 'player_name', default=None) if p is not None else None


@dataclass
class SnapshotMetric:
    match_id: str
    seq: int
    timestamp: Optional[str]
    p1_win: float
    outcome: int
    brier: float
    log_loss: float
    coverage: str


@dataclass
class BacktestReport:
    matches: int
    snapshots: int
    accuracy: float
    brier: float
    log_loss: float
    pre_match_brier: float
    pre_match_log_loss: float
    baseline_brier: float
    baseline_log_loss: float
    by_coverage: dict
    checkpoints: list[int]


class LiveHistoricalBacktester:
    """Leakage-safe evaluator for Vika live predictions on historical point tapes.

    A prediction at sequence N only sees tape rows <= N. The final winner is used
    solely as the outcome label after the fact. Matches with incomplete/ambiguous
    final outcomes are skipped rather than guessed.
    """
    def __init__(self, engine, checkpoint_points=(1, 5, 10, 20, 40, 80, 120)):
        self.engine = engine
        self.checkpoint_points = tuple(int(x) for x in checkpoint_points if int(x) > 0)
        self._prematch = {}

    @staticmethod
    def _outcome(meta: Any, p1: str | None = None, p2: str | None = None) -> Optional[int]:
        w = _get(meta, 'winner', 'winner_id', 'winner_player_id', default=None)
        if isinstance(w, dict):
            wid = _get(w, 'id', 'player_id', default=None)
            wname = _get(w, 'name', 'full_name', 'player_name', default=None)
            if p1 and (wname == p1): return 1
            if p2 and (wname == p2): return 0
            if wid is not None:
                # Match IDs are provider-specific; only accept explicit side labels.
                side = str(_get(w, 'side', default='')).lower()
                if side in ('p1','player1','1','a'): return 1
                if side in ('p2','player2','2','b'): return 0
        elif w is not None:
            ws = str(w).lower()
            if p1 and ws == str(p1).lower(): return 1
            if p2 and ws == str(p2).lower(): return 0
            if ws in ('p1','player1','1','a'): return 1
            if ws in ('p2','player2','2','b'): return 0
        result = str(_get(meta, 'result', 'outcome', default='')).lower()
        if result in ('p1', 'player1', '1', 'a'): return 1
        if result in ('p2', 'player2', '2', 'b'): return 0
        return None

    @staticmethod
    def _point_frame(row: Any):
        # Preserve only fields available at this row. Never attach final metadata.
        if isinstance(row, dict):
            return dict(row)
        return getattr(row, '__dict__', {})

    def _predict(self, prior: float, frame: Any):
        # Import lazily to keep offline training dependencies lightweight.
        from vika_engine.live.model import LiveWinModel
        model = LiveWinModel(prior)
        lf = model.from_frame(prior, frame)
        # The point itself is observed only after it happens. For a prediction at
        # sequence N callers should pass the state represented by N, which is the
        # standard filtering convention for live forecasting the next state.
        return model.predict(lf)

    def run_match(self, tape: dict, match_id='unknown') -> list[SnapshotMetric]:
        meta = tape.get('meta', {}) if isinstance(tape, dict) else {}
        rows = tape.get('tape', tape.get('points', [])) if isinstance(tape, dict) else []
        if not rows:
            return []
        match_obj = tape.get('match', {}) if isinstance(tape, dict) else {}
        p1 = _name(match_obj, 1) or _name(meta, 1) or _name(tape, 1) or _get(match_obj, 'player1_name', default=None)
        p2 = _name(match_obj, 2) or _name(meta, 2) or _name(tape, 2) or _get(match_obj, 'player2_name', default=None)
        match_obj = tape.get('match', {}) if isinstance(tape, dict) else {}
        if not p1: p1 = _get(match_obj, 'player1_name', default=None)
        if not p2: p2 = _get(match_obj, 'player2_name', default=None)
        outcome = self._outcome(match_obj or meta, p1, p2)
        if outcome is None:
            outcome = self._outcome(meta, p1, p2)
        if outcome is None:
            return []
        if not p1 or not p2:
            return []
        # Engine prediction can be replaced by a caller-provided pre-match prior.
        try:
            pre = self.engine.predict(p1, p2, 'Hard', 3, simulations=1000)
            prior = float(pre['p1_win'])
        except Exception:
            prior = 0.5
        coverage = str(_get(meta, 'coverage', default='unknown'))
        if isinstance(match_obj, dict):
            coverage = str(_get(meta, 'coverage', default=_get(match_obj, 'coverage', default=coverage)))
        self._prematch[str(match_id)] = (prior, outcome)
        out = []
        for i, row in enumerate(rows, 1):
            if i not in self.checkpoint_points:
                continue
            frame = self._point_frame(row)
            # If API supplies an embedded score object, keep it; otherwise accept
            # the flattened fields supported by LiveWinModel.from_frame().
            pred = self._predict(prior, frame)
            p = min(.999999, max(.000001, float(pred.get('p1_win', prior))))
            brier = (p - outcome) ** 2
            ll = -math.log(p if outcome else (1.0 - p))
            seq = int(_get(row, 'seq', default=i) or i)
            ts = _get(row, 'timestamp', default=None)
            out.append(SnapshotMetric(str(match_id), seq, ts, p, outcome, brier, ll, coverage))
        return out

    def run(self, matches: Iterable[tuple[str, dict]]) -> BacktestReport:
        all_rows = []
        self._prematch = {}
        for mid, tape in matches:
            all_rows.extend(self.run_match(tape, mid))
        if not all_rows:
            return BacktestReport(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, math.log(2), {}, list(self.checkpoint_points))
        ps = [r.p1_win for r in all_rows]
        ys = [r.outcome for r in all_rows]
        acc = sum((p >= .5) == bool(y) for p, y in zip(ps, ys)) / len(ys)
        brier = statistics.fmean(r.brier for r in all_rows)
        ll = statistics.fmean(r.log_loss for r in all_rows)
        pre_pairs = list(self._prematch.values())
        pre_brier = statistics.fmean((p-y)**2 for p,y in pre_pairs) if pre_pairs else 0.0
        pre_ll = statistics.fmean(-math.log(min(.999999,max(.000001,p if y else 1-p))) for p,y in pre_pairs) if pre_pairs else 0.0
        groups = {}
        for r in all_rows:
            groups.setdefault(r.coverage, []).append(r)
        by_cov = {}
        for k, rows in groups.items():
            by_cov[k] = {
                'snapshots': len(rows),
                'brier': statistics.fmean(r.brier for r in rows),
                'log_loss': statistics.fmean(r.log_loss for r in rows),
            }
        return BacktestReport(
            matches=len({r.match_id for r in all_rows}), snapshots=len(all_rows),
            accuracy=acc, brier=brier, log_loss=ll,
            pre_match_brier=pre_brier, pre_match_log_loss=pre_ll,
            baseline_brier=0.25, baseline_log_loss=math.log(2),
            by_coverage=by_cov, checkpoints=list(self.checkpoint_points),
        )
