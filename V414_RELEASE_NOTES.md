# V4.14 release notes

- Added `scripts_v414_sync.py` for date-bounded completed-match synchronization from Live Tennis API.
- Added robust pagination and 429 retry handling.
- Added deduplication by API match id and date/player signature.
- Added `--rebuild-state` to combine the bundled 2015–2025 archive with synced 2026 results.
- Added `scripts_v414_healthcheck.py`.
- Added `START_HERE_V414.md`.
- Deliberately does not fabricate service stats for API result-list rows; only chronology-dependent state is refreshed.
- Existing V4.7 live ML and V4.10 walk-forward components remain intact.
