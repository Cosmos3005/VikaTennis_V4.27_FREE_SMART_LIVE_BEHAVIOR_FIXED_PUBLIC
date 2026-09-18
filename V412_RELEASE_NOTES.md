# V4.12 Release Notes

- Promoted the supplied 2015–2025 archive to the canonical historical corpus.
- Added `scripts_v412_data_engine.py` for leakage-safe chronological feature generation.
- Added `scripts_v412_train.py` for chronological XGBoost training with validation calibration checks.
- Added V4.12 tests and kept all prior V4.2–V4.11 tests.
- The full 605k-match feature materialization is intentionally an offline build step because the supplied archive is large; the packaged pipeline performs it locally without requiring an external API key.
- No fabricated live backtest metrics are included.
