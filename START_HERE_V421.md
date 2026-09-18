# VikaTennis V4.21 — запуск

## 1. Установка

```bash
python -m pip install -r requirements_v47.txt
```

## 2. Конфигурация

Скопируй `.env.example` в `.env` и укажи:

- `TELEGRAM_BOT_TOKEN` — обязательно для Telegram;
- `LIVETENNISAPI_KEY` — опционально, но нужен для реального LIVE и WebSocket.

## 3. Проверка

```bash
python scripts_v418_healthcheck.py --json
python scripts_v420_production_audit.py
```

## 4. Запуск

```bash
python start_bot.py
```

Команды: `/start`, `/predict`, `/form`, `/h2h`, `/live`, `/errors`, `/status`, `/health`, `/model`.

## 5. Важное перед боевыми ставками

Встроенная база матчей заканчивается 2025-12-29. Поэтому сначала обнови player-state свежими матчами 2026 года. Не выдаём старые данные за live-форму.

V4.21 добавляет point-level Monte Carlo как отдельный слой. Он включается только при наличии реальных service/point features; при их отсутствии бот честно пишет `OFF` и не выдумывает PBP.
