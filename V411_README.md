# VikaTennis V4.11 — Archive Fusion

This release uses the supplied `all_matches_2015_2025.csv` archive as the canonical match-level history. The archive contains 612,124 rows spanning late 2014 through 2025; V4.11 filters the research window strictly to 2015-01-01 through 2025-12-31 and keeps ATP/WTA labels.

For live point-by-point training, V4.11 adds an optional downloader for the public Jeff Sackmann Grand Slam point-by-point repository (2015–2025). It does not fabricate live timestamps: those public tapes are post-match point sequences. Live-observed timestamps remain a separate provenance class and must not be inferred.

## Audit

```bash
python scripts_v411_archive_fusion.py
```

## Download public PBP supplement

```bash
python scripts_v411_archive_fusion.py --download-pbp
```

This downloads available Grand Slam `*-points.csv` files into `data/pbp_public/`. Missing years/events are recorded rather than treated as failures.

## Important modeling rule

The match archive is suitable for pre-match features and labels. It must not be used as if its final-match statistics were known before the match. Post-match fields such as aces, first-serve points won, break points saved, etc. are never allowed as pre-match features.

The public Grand Slam PBP supplement can be used to reconstruct point-state snapshots, but without timestamps those snapshots are labeled `reconstructed`, not `live_observed`.

Sources: Jeff Sackmann's `tennis_atp`, `tennis_wta`, and `tennis_slam_pointbypoint`, CC BY-NC-SA 4.0, non-commercial with attribution.
