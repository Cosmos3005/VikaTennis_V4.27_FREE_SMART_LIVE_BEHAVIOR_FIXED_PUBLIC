# START HERE — VikaTennis V4.16

V4.16 is the Champion Training release. It is the next step after V4.15 point-by-point ingestion.

### If you have historical tape JSONL
```bash
python scripts_v416_train_champion.py --history-jsonl data/live_history.jsonl
```

The report is written to `models/vika_live_v416.report.json`.

### What counts as a real result
Do not use the synthetic smoke-test numbers from development. For a production decision, run on real historical point-by-point tapes and inspect the chronological test block.

### Current roadmap
- V4.15: point-by-point ingestion ✅
- V4.16: champion training framework ✅
- V4.17: multi-fold walk-forward champion selection
- V4.18: production freeze, live stream reconciliation, model/drift health
