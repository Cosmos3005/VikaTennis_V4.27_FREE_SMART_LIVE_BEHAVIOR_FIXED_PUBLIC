from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'models'
DATA = ROOT / 'data'

def root_path(value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p
