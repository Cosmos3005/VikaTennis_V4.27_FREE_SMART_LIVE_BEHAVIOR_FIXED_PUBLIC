# VikaTennis V4.12 — Historical Data Engine

V4.12 uses the supplied 2015–2025 archive as the canonical historical match corpus and adds a leakage-safe chronological feature engine.

## Included corpus
- `data/archive/all_matches_2015_2025.csv.gz`
- Window enforced: 2015-01-01 through 2025-12-31.
- Match-level stats are never exposed to a pre-match prediction row; they are used only after the row is created to update player state.

## Build
```bash
python scripts_v412_data_engine.py \
  --source data/archive/all_matches_2015_2025.csv.gz \
  --out data/v412_features.csv.gz
```

For a faster legacy-compatible feature build:
```bash
python build_training_v42_fast.py --source data/archive/all_matches_2015_2025.csv.gz --out data/v412_features.csv --start-year 2015
```

## Train
```bash
python scripts_v412_train.py --source data/v412_features.csv.gz
```

## Design rules
1. Chronological ordering by tournament date and match number.
2. Features are captured before each match.
3. Post-match serve statistics update the player state only after the snapshot is created.
4. Winner/loser rows are flipped to create two perspectives with inverted targets.
5. No provider live win-probability field is used as a training feature.
6. The resulting model is compatible with the existing V4.2 model interface.

## Public point-by-point supplementation
`data/pbp_public/` can be populated with public Grand Slam point-by-point files by `scripts_v411_archive_fusion.py --download-pbp`. Those data are kept separate from the canonical match archive and are not mislabeled as observed live timestamps.

## Validation
Run:
```bash
pytest -q
```
The release was validated with the full local test suite before packaging.
