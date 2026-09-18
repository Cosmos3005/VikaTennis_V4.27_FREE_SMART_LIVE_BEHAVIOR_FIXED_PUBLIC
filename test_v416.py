import json,tempfile
from pathlib import Path
from vika_engine.training.history_tape import normalize_tape
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47

def make(mid,day,winner):
    pts=[]
    for i in range(20): pts.append({'seq':i+1,'point_winner':1 if (i+winner)%3 else 2,'server':1 if i%2==0 else 2})
    return normalize_tape({'match':{'id':mid,'date':day,'player1_name':'A','player2_name':'B','winner':winner},'tape':pts},source='livetennis_observed')

def test_builder_uses_point_winner_not_match_winner():
    t=make('m','2025-01-01',2); s=LiveSnapshotBuilderV47(max_snapshots_per_match=10).build([('m',t)])
    assert s and any(x.features['momentum_sample']>0 for x in s)

def test_no_same_match_split_logic():
    from vika_engine.training.champion_v416 import _split
    snaps=[]
    b=LiveSnapshotBuilderV47(max_snapshots_per_match=4)
    for i in range(30): snaps += b.build([(f'm{i}',make(f'm{i}',f'2025-{(i%9)+1:02d}-01',1 if i%2 else 2))])
    tr,va,te=_split(snaps)
    a={s.match_id for s in tr}; c={s.match_id for s in va}; d={s.match_id for s in te}
    assert not(a&c or a&d or c&d)
