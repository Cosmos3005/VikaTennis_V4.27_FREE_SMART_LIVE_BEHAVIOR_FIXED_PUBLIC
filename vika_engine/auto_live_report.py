from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import threading
from typing import Any


class AutoLiveReport:
    """Persistent JSONL diagnostics for AUTO-LIVE scans.

    One record per scan is appended to data/auto_live/YYYY-MM-DD.jsonl.
    The file is intentionally human-readable and easy to archive/analyse later.
    """

    def __init__(self, root: str = "data/auto_live"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, when: datetime | None = None) -> Path:
        when = when or datetime.now(timezone.utc)
        return self.root / f"{when:%Y-%m-%d}.jsonl"

    def record_scan(self, payload: dict[str, Any]) -> None:
        row = {"ts": datetime.now(timezone.utc).isoformat(), **payload}
        path = self._path()
        with self._lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def today_summary(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        path = self._path(now)
        if not path.exists():
            return {"date_utc": now.strftime("%Y-%m-%d"), "scans": 0}

        scans = 0
        matches = 0
        analyzed = 0
        candidate_markets = 0
        signals = 0
        api_errors = 0
        reasons = Counter()
        markets = Counter()
        durations = []

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                scans += 1
                matches += int(row.get("matches_found", 0) or 0)
                analyzed += int(row.get("matches_analyzed", 0) or 0)
                candidate_markets += int(row.get("candidate_markets", 0) or 0)
                signals += int(row.get("signals", 0) or 0)
                api_errors += int(row.get("api_errors", 0) or 0)
                for k, v in (row.get("reasons") or {}).items():
                    reasons[k] += int(v or 0)
                for k, v in (row.get("markets") or {}).items():
                    markets[k] += int(v or 0)
                if row.get("duration_sec") is not None:
                    try:
                        durations.append(float(row["duration_sec"]))
                    except Exception:
                        pass

        return {
            "date_utc": now.strftime("%Y-%m-%d"),
            "scans": scans,
            "matches_found": matches,
            "matches_analyzed": analyzed,
            "candidate_markets": candidate_markets,
            "signals": signals,
            "api_errors": api_errors,
            "reasons": dict(reasons),
            "markets": dict(markets),
            "avg_scan_sec": round(sum(durations) / len(durations), 1) if durations else None,
            "report_path": str(path),
        }

    def format_today(self) -> str:
        s = self.today_summary()
        if not s.get("scans"):
            return "📊 AUTO-LIVE: сегодня записей пока нет."
        reasons = s.get("reasons") or {}
        markets = s.get("markets") or {}
        lines = [
            "📊 <b>VIKA AUTO-LIVE — ОТЧЁТ</b>",
            f"Сканирований: <b>{s['scans']}</b>",
            f"LIVE-матчей увидено: <b>{s['matches_found']}</b>",
            f"Матчей проанализировано: <b>{s['matches_analyzed']}</b>",
            f"Кандидатных рынков: <b>{s['candidate_markets']}</b>",
            f"Сигналов: <b>{s['signals']}</b>",
            f"Ошибок API: <b>{s['api_errors']}</b>",
        ]
        if reasons:
            lines.append("\n<b>Почему PASS:</b>")
            labels = {
                "no_signal": "не прошёл фильтр",
                "conflict": "конфликт PRE/LIVE",
                "no_market": "нет подходящего рынка",
                "no_price": "нет реального коэффициента",
                "no_value": "нет достаточного value",
                "insufficient_data": "недостаточно данных",
                "invalid_match": "неполный матч",
                "analysis_error": "ошибка расчёта",
            }
            for k, v in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"• {labels.get(k, k)}: <b>{v}</b>")
        if markets:
            lines.append("\n<b>Рынки-кандидаты:</b>")
            for k, v in sorted(markets.items(), key=lambda x: (-x[1], x[0])):
                lines.append(f"• {k}: <b>{v}</b>")
        if s.get("avg_scan_sec") is not None:
            lines.append(f"\nСреднее время скана: <b>{s['avg_scan_sec']} сек</b>")
        lines.append(f"\nФайл: <code>{s['report_path']}</code>")
        return "\n".join(lines)
