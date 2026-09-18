# V4.18 — Production Freeze

V4.18 is the production-oriented freeze after the V4.15 point engine, V4.16 champion training layer and V4.17 walk-forward evaluation layer.

## Added
- reconnect-safe ULTRA WebSocket client;
- REST point catch-up using `after_seq`;
- monotonic `seq` deduplication and point reconciler;
- automatic fresh WebSocket token on reconnect;
- `/status` and `/model` Telegram commands;
- production model artifact auto-selection: V4.17 -> V4.16 -> V4.7;
- production healthcheck script;
- explicit model/state/API health visibility.

The point stream is treated as an event stream. Missed point events are recovered from REST and deduplicated by the upstream per-match `seq` cursor. Coverage is accepted as partial: a match without point coverage is not converted into fake point data.

## Verification
- syntax compilation: required;
- unit tests: V4.17 baseline + production additions;
- offline WebSocket/reconciler tests do not require an API key.

## Important
V4.18 does not claim that live point coverage is universal. The upstream API documents `pbp_coverage=point` versus `game`, and REST catch-up is the recovery mechanism for missed WebSocket point events.
