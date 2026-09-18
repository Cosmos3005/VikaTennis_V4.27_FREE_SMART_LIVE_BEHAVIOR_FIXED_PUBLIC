# VikaTennis V4.16 — Champion Live Model

## Что добавлено
- Explicit chronological train/validation/test split by whole match IDs.
- Live XGBoost trained only on causal point-by-point snapshots.
- Validation-only champion selection by log loss, then Brier.
- Pre-match prior is a mandatory benchmark.
- Platt calibration is tested on validation and only deployed when it wins validation selection.
- Calibrated model is serialized as a production-compatible object and loaded by the live ML adapter.
- Point-level `point_winner` remains separate from match-level `winner`.

## Важно
V4.16 **не содержит выдуманных historical live metrics**. Реальные цифры появляются только после загрузки реальных historical tape JSONL from Live Tennis API / other approved point sources.

## Training
```bash
python scripts_v416_train_champion.py \
  --history-jsonl data/live_history.jsonl \
  --output models/vika_live_v416.joblib \
  --report models/vika_live_v416.report.json
```

The resulting artifact exposes `predict_proba()` and is compatible with the existing live adapter.

## Validation
- 28 tests passed.
- Python compilation passed.
- End-to-end synthetic training smoke test passed.
