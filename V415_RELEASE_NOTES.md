# V4.15 — Point-by-Point Data Engine

V4.15 adds a canonical historical point-tape ingestion layer and causal snapshot materialization.

## What changed
- Normalizes Live Tennis API history tapes, reconstructed tapes, and public PBP sources into one schema.
- Adds explicit provenance: `observed_live`, `reconstructed`, `sackmann_public`.
- Prevents the match-level `winner` field from being silently treated as a point winner.
- Deduplicates tapes by match id.
- Materializes causal live snapshots using the existing V4.7 feature schema.
- Keeps provider `win_probability_p1` / `danger` out of model features.
- Adds tests for leakage and point-winner handling.

## Important
This release does **not** claim a new trained live model. Real historical tapes are required for V4.16 training. The release contains the engine to ingest/materialize them reproducibly.
