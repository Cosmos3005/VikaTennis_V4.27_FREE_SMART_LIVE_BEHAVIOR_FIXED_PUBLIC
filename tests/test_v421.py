from pathlib import Path
from vika_engine.point_simulator import simulate_match
from vika_engine.paths import ROOT
from vika_engine.model_health import ModelHealth

def test_point_mc_shape():
    r=simulate_match(.64,.60,best_of=3,simulations=300,seed=7)
    assert 0 < r['p1_win'] < 1
    assert abs(r['p1_win']+r['p2_win']-1) < 1e-12
    assert r['expected_total'] > 0
    assert r['top_scores']

def test_root_paths_are_project_local():
    assert (ROOT/'models/vika_models_v42.joblib').exists()
    assert ModelHealth().model_path == ROOT/'models/vika_models_v42.joblib'
