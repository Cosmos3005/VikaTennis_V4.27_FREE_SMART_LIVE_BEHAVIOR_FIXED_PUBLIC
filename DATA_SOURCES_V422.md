# VikaTennis V4.22 — data policy

## Primary production source
Live Tennis API is the preferred production source because the current Vika stack already uses it for live scores/WebSocket/history and it provides documented historical match tapes from 2023→now, plus reconstructed 2013–2022 tapes. Point coverage is measured per match; `game` coverage is never promoted to point-by-point.

## Research/backtest source
Jeff Sackmann ATP/WTA datasets are useful for long historical training and match statistics. The public archive is CC BY-NC-SA 4.0, so it is **non-commercial** unless separate permission is obtained. Do not package Sackmann-derived data into a paid/commercial Vika distribution without resolving the license.

## Open Tennis Data v3
`ryantjx/tennis-match-data` publishes verified ATP/WTA top-level main-draw research data as Parquet through GitHub Releases. Its software is MIT, but the published data has source-specific obligations. Treat it as a research source, not automatically commercial-safe data.

## Point-by-point policy
- `point` coverage: eligible for point-level features and point Monte Carlo.
- `game` coverage: eligible only for game/set/match state features; never converted into fake points.
- `reconstruction`: eligible for structural point-state modeling, but it has no real timestamps and no historical live-model outputs.
- missing coverage: fallback to ordinary match statistics.

## Current-date limitation
Public mirrors found in the research are not a substitute for a live current feed. The Sackmann archive mirror reports ATP/WTA snapshots through 2026, while Open Tennis Data v3 currently documents preview releases and a July 24, 2026 example release. Therefore Vika uses the official API for the final 2026 refresh rather than silently treating a stale public snapshot as current.
