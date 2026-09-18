# VikaTennis V4.25 HOTFIX

This hotfix fixes the broken production handoff in V4.24.

## Fixed
- Windows BAT files now install the required Python packages before importing pandas.
- Today's/upcoming fixtures come from `GET /matches?status=upcoming`, rather than from the historical database. Historical data is for player state; today's fixture is a separate current-state object.
- Russian player input is resolved against today's official fixture list, including `Соболенко -> Aryna Sabalenka` and `Пегула -> Jessica Pegula` plus fuzzy matching.
- `/day`, `/today`, `/upcoming` generate the day's available pre-match forecasts.
- `/live MATCH_ID` calculates the current live probability.
- `/watch MATCH_ID` pushes live probability/score updates approximately every minute.
- Existing model/state files are not deleted by a failed refresh.

## First run
1. Keep the existing `.env` with your API key and Telegram token.
2. Run `run_vika.bat` once. It installs dependencies, refreshes history/state/model, then starts the bot.
3. For bot-only launch use `start_bot.bat`.
4. In Telegram: `Соболенко Пегула хард` or `/day`.

## Important API tier note
Current/upcoming matches are available on the FREE Live Tennis API tier. Historical completed matches require the History/BASIC entitlement. The bot can see today's fixture without history, but the full Vika pre-match model still needs historical player state; therefore run the refresh when the key has History access.
