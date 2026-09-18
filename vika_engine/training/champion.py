from __future__ import annotations

def should_promote(challenger: dict, champion: dict, min_logloss_gain=0.002, min_brier_gain=0.001) -> bool:
    if not champion: return True
    cl=float(challenger.get('test_logloss',1e9)); pl=float(champion.get('test_logloss',1e9))
    cb=float(challenger.get('test_brier',1e9)); pb=float(champion.get('test_brier',1e9))
    return (pl-cl)>=min_logloss_gain and (pb-cb)>=min_brier_gain
