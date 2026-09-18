# VikaTennis v4.6 — Historical Live Backtest

## Что сделано

v4.6 добавляет настоящий historical live-backtest слой. Он проверяет Vika на исторической последовательности матча и считает вероятность только из состояния, доступного на соответствующем checkpoint.

Важно: итоговый победитель используется **только как label после матча**. Он не передаётся в live state. Это защищает backtest от look-ahead leakage.

## Метрики

- live accuracy
- live Brier score
- live Log Loss
- pre-match Brier / Log Loss
- 50/50 baseline
- разбивка по coverage
- заданные point checkpoints

Главный критерий улучшения — не просто accuracy, а снижение Log Loss/Brier относительно pre-match модели на том же наборе матчей.

## Live Tennis API

Для 2023+ API предоставляет `/history/matches/{matchId}` с point-by-point tape; документация отдельно указывает, что coverage может быть неполной. Для live ULTRA point stream используется `seq`, а восстановление пропущенных событий делается через `/matches/{matchId}/points?after_seq=...`.

Для 2013–2022 существует отдельный reconstructed archive tape. Он не имеет реальных timestamps и model probabilities, поэтому v4.6 не выдаёт такие строки за реально наблюдавшиеся live snapshots.

## Запуск

Нужен `LIVETENNISAPI_KEY`:

```bash
python scripts_v46_backtest.py MATCH_ID [MATCH_ID ...] --complete
```

Результат:

```text
models/live_backtest_v46.json
```

## Как выбирать production live model

Не переключать production только потому, что одна выборка дала лучший accuracy.

Минимально:

1. взять репрезентативную выборку матчей;
2. разделить её по времени;
3. проверить point coverage;
4. сравнить pre-match и live на одинаковых snapshots;
5. посмотреть Brier/Log Loss по checkpoint;
6. отдельно проверить ATP/WTA, surface и tour level;
7. только после этого менять live blending.

v4.6 специально не заявляет ROI/profitability — это следующий отдельный эксперимент с историческими odds и timestamped market prices.
