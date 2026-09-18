from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PointReconciler:
    """Idempotent point cursor for WS + REST catch-up.

    The upstream `seq` is the only ordering/dedup key. A reconnect never
    blindly appends an already-seen point.
    """
    match_id: str
    last_seq: int = 0
    points: list[dict[str, Any]] = field(default_factory=list)
    basis: str | None = None
    quality: str | None = None

    def ingest(self, rows: list[dict[str, Any]], *, basis: str | None = None, quality: str | None = None) -> int:
        # Live capture can later be replaced wholesale by a complete reconstruction.
        # Never merge the two sequences: they have different seq spaces.
        if basis and self.basis and basis != self.basis:
            self.points.clear(); self.last_seq = 0
        added = 0
        seen = {int(p.get("seq", -1)) for p in self.points if p.get("seq") is not None}
        for row in rows or []:
            point = row.get("point") if isinstance(row, dict) and isinstance(row.get("point"), dict) else row
            if not isinstance(point, dict):
                continue
            try: seq = int(point.get("seq"))
            except (TypeError, ValueError):
                continue
            if seq <= 0 or seq in seen:
                continue
            point = dict(point); point["seq"] = seq
            self.points.append(point); seen.add(seq); added += 1
        self.points.sort(key=lambda x: int(x.get("seq", 0)))
        if self.points: self.last_seq = max(self.last_seq, int(self.points[-1]["seq"]))
        if basis: self.basis = basis
        if quality: self.quality = quality
        return added

    def snapshot(self) -> dict[str, Any]:
        return {"match_id": self.match_id, "last_seq": self.last_seq,
                "points": list(self.points), "basis": self.basis, "quality": self.quality}

    @property
    def contiguous(self) -> bool:
        return not self.points or [int(p["seq"]) for p in self.points] == list(range(1, self.last_seq + 1))
