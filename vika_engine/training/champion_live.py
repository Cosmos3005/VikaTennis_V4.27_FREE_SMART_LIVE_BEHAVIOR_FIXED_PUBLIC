from __future__ import annotations
import json, math
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from .live_model_v47 import LiveSnapshotBuilderV47, LiveModelV47, Snapshot, FEATURES


def _safe_logloss(y, p):
    if not y: return 0.0
    return float(log_loss(y, np.clip(p, 1e-6, 1-1e-6), labels=[0,1]))


def metrics(snaps: list[Snapshot], probs: list[float]):
    y=[s.target for s in snaps]
    p=np.clip(np.asarray(probs,dtype=float),1e-6,1-1e-6)
    return {
        'n_snapshots': len(y),
        'n_matches': len({s.match_id for s in snaps}),
        'accuracy': float(accuracy_score(y,p>=.5)) if y else 0.0,
        'brier': float(brier_score_loss(y,p)) if y else 0.0,
        'log_loss': _safe_logloss(y,p.tolist()),
    }


def pre_match_probs(snaps: list[Snapshot]):
    return [1.0/(1.0+math.exp(-s.features.get('prior_logit',0.0))) for s in snaps]


def v47_probs(model, snaps):
    return [model.predict_proba(s.features) for s in snaps]


def conservative_mc_proxy(s: Snapshot):
    # Deterministic proxy used only for a fair offline benchmark when the full
    # point-by-point Monte Carlo engine is not available to historical snapshots.
    prior=1/(1+math.exp(-s.features.get('prior_logit',0.0)))
    z=(0.85*math.tanh(s.features.get('sets_diff',0)*1.8)
       +0.18*math.tanh(s.features.get('games_diff',0)/3.0)
       +0.10*math.tanh(s.features.get('point_diff',0)/2.0)
       +0.22*s.features.get('momentum_ewma',0))
    return 1/(1+math.exp(-(math.log(prior/(1-prior))+z)))


def evaluate_champion(model_path: str, snaps: list[Snapshot], output: str|None=None):
    model=LiveModelV47.load(model_path)
    methods={
        'pre_match_v42_prior': pre_match_probs(snaps),
        'v47_live_xgb': v47_probs(model,snaps),
        'v47_plus_live_state_proxy': [0.65*a+0.35*b for a,b in zip(v47_probs(model,snaps),[conservative_mc_proxy(s) for s in snaps])],
    }
    report={'model_path':model_path,'champion_rule':'lowest test log_loss, then lowest brier','models':{k:metrics(snaps,v) for k,v in methods.items()}}
    ranked=sorted(report['models'].items(),key=lambda kv:(kv[1]['log_loss'],kv[1]['brier']))
    report['ranking']=[k for k,_ in ranked]
    report['champion']=ranked[0][0] if ranked else None
    if output:
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
