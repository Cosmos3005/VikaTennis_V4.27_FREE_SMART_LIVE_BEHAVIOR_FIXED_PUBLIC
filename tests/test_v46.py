import math
from vika_engine.training.live_backtest import LiveHistoricalBacktester

class DummyEngine:
    def predict(self,*a,**k): return {'p1_win': .6}

def tape():
    return {
      'match': {'player1_name':'A','player2_name':'B','winner':1},
      'meta': {'coverage':'point'},
      'tape': [
        {'seq':1,'timestamp':'2026-01-01T10:00:00Z','sets':[0,0],'games':[0,0]},
        {'seq':2,'timestamp':'2026-01-01T10:01:00Z','sets':[0,0],'games':[1,0]},
        {'seq':3,'timestamp':'2026-01-01T10:02:00Z','sets':[1,0],'games':[0,0]},
      ]
    }

def test_backtest_is_causal_and_uses_final_only_as_label():
    bt=LiveHistoricalBacktester(DummyEngine(), checkpoint_points=(1,2))
    rows=bt.run_match(tape(),'m1')
    assert len(rows)==2
    assert all(r.outcome==1 for r in rows)
    assert rows[0].seq==1 and rows[1].seq==2
    assert rows[0].timestamp.endswith('Z')

def test_report_baselines_and_metrics():
    bt=LiveHistoricalBacktester(DummyEngine(), checkpoint_points=(1,))
    r=bt.run([('m1',tape())])
    assert r.matches==1 and r.snapshots==1
    assert r.pre_match_brier < .25
    assert r.brier < .25
    assert math.isclose(r.baseline_brier,.25)
    assert math.isclose(r.baseline_log_loss,math.log(2))
