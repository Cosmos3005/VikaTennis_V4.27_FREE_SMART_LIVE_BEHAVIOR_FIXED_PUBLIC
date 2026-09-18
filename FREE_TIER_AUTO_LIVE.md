# Vika — Free Live Tennis API mode

The Live Tennis API FREE tier is 30 requests/minute and 100 requests/day. `GET /usage` is quota-exempt.

Vika's automatic monitor therefore does **not** request a separate score for every live match. The live board request returns the live match list/current state, so one request can feed the local scanner for many matches.

Defaults:
- `LIVETENNIS_FREE_DAILY_LIMIT=100`
- `LIVETENNIS_AUTO_DAILY_BUDGET=80`
- `LIVETENNIS_MANUAL_RESERVE=10`
- adaptive AUTO-LIVE interval based on remaining daily budget and time to UTC reset
- live board cache: 30 seconds
- day/upcoming cache: 5 minutes

If the daily reserve is reached, AUTO-LIVE pauses instead of hammering the API. Manual use can still consume the reserved calls. The next day the automatic budget resets.

Recommended status command: `/status` or Russian `статус`.
It reports API health, daily calls/remaining, and the approximate next auto-scan interval.


Hotfix note: /usage uses official Authorization: Bearer authentication; the bot derives remaining_day from limits.per_day and today.calls when remaining_day is null.
