# VikaTennis v4 — what changed

This upgrade keeps the existing project and adds a real pre-match state layer instead of a fixed 65% prediction.

## Included
- leakage-safe baseline XGBoost trained only on pre-match features;
- player state cache through the latest bundled 2026 data;
- recent form 5/10/20 with time decay;
- surface Elo seed and recent surface form;
- service/return rates from completed matches;
- workload/fatigue over 30 days;
- opponent-quality proxy;
- H2H history;
- 100k Monte Carlo with corrected BO3/BO5 logic;
- prediction journal SQLite;
- optional Live Tennis API adapter;
- live-state updater;
- Telegram commands `/predict`, `/form`, `/h2h`, `/live`.

## Important
The bundled v4 model is deliberately a **safe baseline**: it uses only information available before a match. Its test accuracy is ~67.5% on the bundled chronological holdout, rather than claiming the old 74.1% number. This is intentional: the previous feature builder included same-match statistics such as aces and service points, which are not known before the match and can inflate apparent performance.

The next model upgrade should add the chronological rolling form/fatigue/surface features from `scripts/build_training_v4.py`, then compare them by walk-forward log loss, Brier score and calibration.

## Live API
The official Live Tennis API SDK is optional. Put `LIVETENNISAPI_KEY` in `.env`. FREE provides live/upcoming data; historical endpoints require a History/BASIC entitlement; the WebSocket feed is ULTRA. The code uses a provider abstraction so the core engine does not depend on one vendor.

## V4.1 additions
- ATP-only live state snapshot built from the latest available season in the supplied dataset.
- Glicko-2 style uncertainty state is stored alongside Elo and exposed to the prediction layer.
- Pre-match features remain leakage-safe: post-match statistics are not used as predictors.
- Probability calibration hook (Platt scaling) is supported by `VikaModels`; legacy models fall back safely.
- Confidence is reported as HIGH/MEDIUM/LOW and is separated from raw win probability.
- Champion/challenger registry and promotion gate added under `vika_engine/model_registry.py` and `vika_engine/training/champion.py`.
- Three regression tests cover simulator validity, confidence, and model promotion gating.

### Important
The supplied historical CSV is very large and contains both ATP and WTA rows. Training/build scripts filter to ATP before feature generation. Do not train on `data/atp_features.csv` for production without auditing it for post-match leakage.

## V4.2 challenger

V4.2 rebuilds the two-perspective dataset from the canonical winner rows, fixing the previous flipped-row bug where `target_win=0` could still retain winner-oriented player names/features.

The production candidate is `models/vika_models_v42.joblib` (also copied to `vika_models_v42.joblib` for simple launch). The bot defaults to the V4.2 model.

Chronological holdout (not random split):
- train: 185,584 rows
- validation: 37,182 rows
- test: 27,536 rows
- test window: 2025-07-27 through 2025-12-29
- accuracy: 69.59%
- log loss: 0.5723
- Brier: 0.1953

A simple rank-only baseline on the same test window scored 59.97% accuracy, 1.1944 log loss and 0.3084 Brier. The model is therefore meaningfully better than the baseline, but this is not a claim of future performance.

Calibration is gated: if Platt calibration worsens validation log loss, V4.2 keeps the raw XGBoost probabilities instead of deploying the calibration layer. XGBoost early stopping is used on the chronological validation period.
