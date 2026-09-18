# V4.7 release notes

- Added causal historical live snapshot builder.
- Added XGBoost live model trainer with chronological whole-match split.
- Added automatic V4.7 live-model adapter to PredictionEngine.
- Added JSONL history ingestion and direct Live Tennis API history fetcher.
- Added healthcheck and installation requirements.
- Vendor live probability and vendor danger fields are excluded from V4.7 features to avoid provider imitation/leakage.
- Early stopping uses XGBoost callback `EarlyStopping(save_best=True)`.
- If no trained V4.7 artifact exists, live predictions automatically fall back to the previously tested v4.5 estimator.
- 15 offline tests pass.

## V4.8 pipeline preparation — last 5 years

Added `scripts_v48_pipeline.py` to automatically collect the last five calendar-date years requested (default 2021-09-08 through 2026-09-08): reconstructed archive tapes for 2021-2022 and current point-by-point tape packages for 2023-present. The pipeline defaults to ATP/WTA singles and rejects clearly partial/no-coverage tapes unless `--include-partial` is supplied. It stores compressed JSONL locally, filters by exact date window, and can launch the V4.7 trainer.

The API documentation confirms that 2023-present history is the observed point-by-point half, while 2013-2022 archive tapes are reconstructed; the pipeline keeps those sources distinguishable in the downloaded directories.
