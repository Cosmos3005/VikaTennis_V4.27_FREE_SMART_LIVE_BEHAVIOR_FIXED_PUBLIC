from vika_engine.training.history_tape import normalize_tape
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47
from vika_engine.training.walk_forward_v417 import _partition

def make(mid,day,winner):
    pts=[]
    for i in range(30): pts.append({'seq':i+1,'point_winner':1 if i%3 else 2,'server':1 if i%2==0 else 2})
    return normalize_tape({'match':{'id':mid,'date':day,'player1_name':'A','player2_name':'B','winner':winner},'tape':pts},source='livetennis_observed')

def test_walk_forward_date_partition_is_atomic():
    b=LiveSnapshotBuilderV47(max_snapshots_per_match=8)
    snaps=[]
    for i,day in enumerate(['2023-12-01','2024-01-02','2024-03-01','2025-02-01','2025-05-01','2026-02-01']):
        t=make(f'm{i}',day,1 if i%2 else 2); snaps += b.build([(f'm{i}',t)])
    tr,te=_partition(snaps,'2023-12-31','2024-01-01','2024-12-31')
    assert {s.match_id for s in tr} == {'m0'}
    assert {s.match_id for s in te} == {'m1','m2'}
    assert not ({s.match_id for s in tr} & {s.match_id for s in te})

def test_point_winner_does_not_equal_match_winner():
    t=make('x','2025-01-01',2)
    snaps=LiveSnapshotBuilderV47(max_snapshots_per_match=8).build([('x',t)])
    assert snaps and all(s.target==0 for s in snaps)
