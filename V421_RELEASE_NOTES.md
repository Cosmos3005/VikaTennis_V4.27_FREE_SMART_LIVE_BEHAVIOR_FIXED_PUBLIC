# VikaTennis V4.21 — Launch Hardening

V4.21 is the operational patch on top of V4.20.

## What changed
- Project-root-safe paths: the bot no longer depends on the shell's current working directory.
- Production healthcheck uses absolute project-root resolution.
- Added a real point → game → set → match Monte Carlo layer using service-point probabilities when those features exist.
- Point-level simulation is explicitly marked unavailable when there is no point/service evidence; no fake PBP is generated.
- Prematch output exposes the point-MC layer separately from the calibrated winner model.
- Existing live fallback remains unchanged and is still the primary live estimator until a real historical live champion is trained on holdout tapes.

## Important
The bundled match database ends in 2025-12-29. For September 2026 production use, refresh the player state before trusting prematch form/fatigue as current.

The current historical dataset is useful for training, but it is not a substitute for a 2026 refresh.
