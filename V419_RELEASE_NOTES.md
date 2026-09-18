# V4.19 FINAL — Production Audit & Freeze

- Fixed live model adapter fallback/priority so V4.17/V4.16 artifacts are actually loadable when present.
- Fixed point reconciler to replace, rather than merge, a live sequence when the API switches to a complete reconstruction basis.
- Fixed stream catch-up metadata handling and preserved backward-compatible `catch_up_points()` return behavior.
- `/status` and `/model` are now registered Telegram commands.
- Healthcheck now recognizes both player-state variants and reports production readiness explicitly.
- No fabricated live-model metrics are bundled: without a real trained live artifact, the bot uses the tested V4.5 live fallback.
- Production freeze rule: never promote a live champion unless it wins chronological holdouts on logloss/Brier and passes the walk-forward audit.
