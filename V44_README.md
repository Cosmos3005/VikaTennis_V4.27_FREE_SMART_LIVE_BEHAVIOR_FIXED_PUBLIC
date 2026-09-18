# VikaTennis v4.4

V4.4 adds an online point-by-point momentum layer to the v4.3 live engine.

## Live pipeline

`pre-match prior -> score/state -> live stats -> point EWMA momentum -> calibrated live probability`

Momentum is intentionally bounded and sample-size weighted. It cannot replace the pre-match prior after a tiny number of points.

## Live Tennis API integration

For ULTRA point feeds, subscribe to `points`, keep the per-match `seq`, and reconcile missed events with `GET /matches/{matchId}/points?after_seq=<last_seq>`. Deduplicate by `seq`.

If the provider only reports game-level coverage, Vika falls back to score/statistics and does not fabricate point events.

## Training

The momentum layer is currently an online state estimator, not a claim of a trained causal momentum model. Historical point-event training should only be enabled after the point dataset has been audited for timestamp/order leakage.

## Tests

Run:

`python -m pytest -q`

## V4.5 — Live Monte Carlo

V4.5 adds a remainder-of-match Monte Carlo engine. It starts from the pre-match probability, incorporates the current set/game state and sufficiently sampled live serve/return/break-point statistics, then simulates only the unfinished portion of the match.

The engine runs 100,000 simulations by default and exposes:
- `p1_win` / `p2_win`
- next-set probability
- expected remaining sets/games
- inferred live game probability

It deliberately does not fabricate point data when the provider only has game-level coverage. When point-level coverage is available, the existing momentum engine supplies an additional bounded state signal.

LiveTennisAPI's point stream is best-effort and uses a monotonic `seq`; dropped events must be reconciled through the points endpoint using `after_seq`. Coverage must be checked before treating a match as point-level. See the provider documentation for the current protocol. 
