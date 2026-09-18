VikaTennis v4 patch

This patch is designed to be extracted OVER the existing VikaTennis_v3_DeepStats_Simulator folder.
It does NOT contain the large data/raw CSV archive.

Included:
- leakage-safe v4 baseline model
- player state cache through bundled 2026 data
- form/fatigue/H2H/surface state engine
- corrected Monte Carlo BO3/BO5
- prediction journal
- optional Live Tennis API adapter
- live state updater
- new Telegram v4 bot
- scripts for state/model building

Before starting the bot:
1. Put TELEGRAM_BOT_TOKEN in .env.
2. Optionally put LIVETENNISAPI_KEY in .env.
3. Run: python scripts/predict_v4.py --player1 "Carlos Alcaraz" --player2 "Jannik Sinner" --surface Hard
4. Run: python -m pytest -q
5. Start: python vikatenis_v3_bot.py

IMPORTANT: The Telegram token that was hard-coded in the original uploaded project has been removed from the upgraded bot. Rotate/revoke that token in BotFather because it was present in the uploaded source.
