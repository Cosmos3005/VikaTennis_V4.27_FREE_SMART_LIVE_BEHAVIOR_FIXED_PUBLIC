# Vika AUTO-LIVE Multi-Markets

## What Vika now scans

The live scanner is no longer winner-only at the model layer. For every live match it can evaluate:

- match winner;
- game handicap;
- total games Over/Under;
- current-set winner (when the set state is informative);
- total sets Over 2.5 (best-of-three, as a watch/candidate market).

The architecture is intentionally `score/stats -> live model -> market candidates -> real odds -> EV filter -> signal`.

## Important: odds are never invented

Live Tennis API's PRO market feed is currently match-winner prices. For spreads/totals, Vika needs a real multi-market odds feed. The optional adapter is prepared for The Odds API and reads `h2h`, `spreads`, and `totals`.

If `THE_ODDS_API_KEY` is empty, Vika can still scan the markets internally, but it will only auto-signal a market when a real compatible price is available from the Live Tennis API (currently moneyline fallback).

## Auto-signal filters

- hard veto when pre-match and live models strongly conflict;
- minimum model probability / confidence;
- real odds only;
- fair-odds comparison;
- minimum +EV edge;
- per-match/market cooldown to prevent spam;
- no pretending a moneyline quote is a handicap/total quote.

## Why these markets

Public tennis market guides consistently identify moneyline, game handicaps, totals, set markets and player props as the main market families. For an autonomous scanner, game handicaps and totals are especially useful because they can be evaluated from the live score plus a distributional model rather than relying only on the match winner.

Player props such as aces/double faults can be added as a second-stage module when a live stats/props feed is available. They should not be faked from score alone.
