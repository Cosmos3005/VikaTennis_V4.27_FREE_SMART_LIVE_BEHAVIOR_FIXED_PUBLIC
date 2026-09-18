from vika_engine.simulator import MatchSimulator
from vika_engine.calibration import confidence
from vika_engine.training.champion import should_promote

def test_bo3_simulation_is_valid():
    r=MatchSimulator(seed=1).simulate(.6,best_of=3,n=3000)
    assert 0.52 < r['p1_win'] < 0.70
    assert all(len(s.split()) in (2,3) for s,_ in r['top_scores'])

def test_confidence_is_categorical():
    assert confidence(.5,1,.0)=='LOW'
    assert confidence(.9,1,.0)=='HIGH'

def test_champion_gate():
    assert should_promote({'test_logloss':.58,'test_brier':.19},{'test_logloss':.59,'test_brier':.192})
    assert not should_promote({'test_logloss':.589,'test_brier':.1915},{'test_logloss':.59,'test_brier':.192})
