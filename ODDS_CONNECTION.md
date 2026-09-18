# Real live odds connection

Vika now has a production-ready adapter for **The Odds API v4**.

It requests real live/upcoming tennis prices for:

- `h2h` — match winner;
- `spreads` — game handicap;
- `totals` — total games Over/Under.

The provider is deliberately strict about player matching and will refuse to attach odds when it cannot confidently identify the same match.

## One thing still required from the operator

The external odds service requires its own API key. It cannot be generated or recovered from the Live Tennis API key. Put the key into `.env`:

```text
THE_ODDS_API_KEY=YOUR_KEY
```

No key is hard-coded into the package and no odds are invented when the feed is unavailable.

The current The Odds API documentation confirms live/upcoming tennis odds and the `h2h`, `spreads`, and `totals` markets; coverage of spreads/totals can depend on bookmaker/event. Vika therefore treats missing markets as **no bet**, not as a reason to guess.
