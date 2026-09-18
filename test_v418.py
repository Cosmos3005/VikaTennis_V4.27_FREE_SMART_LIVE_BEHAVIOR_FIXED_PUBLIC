from vika_engine.live.reconciler import PointReconciler
from vika_engine.model_health import ModelHealth

def test_reconciler_dedup_and_cursor():
    r=PointReconciler('1')
    assert r.ingest([{'seq':1},{'seq':2}])==2
    assert r.ingest([{'seq':2},{'seq':3}])==1
    assert r.last_seq==3 and r.contiguous

def test_health_shape():
    r=ModelHealth(model_path='models/vika_models_v42.joblib').report()
    assert 'artifacts' in r and r['ok']
