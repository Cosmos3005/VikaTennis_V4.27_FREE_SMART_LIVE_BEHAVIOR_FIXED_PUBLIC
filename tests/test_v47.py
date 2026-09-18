import random
from pathlib import Path
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47, train_live_model
from vika_engine.live.ml import LiveMLAdapterV47


def make_tape(mid, winner):
    rows=[]
    for i in range(1,31):
        lead = (i//5 if winner==1 else -(i//5))
        rows.append({'seq':i,'timestamp':f'2026-01-{1+int(mid):02d}T10:{i:02d}:00Z',
                     'sets':[1,0] if lead>=5 else [0,0],
                     'games':[max(0,3+lead),2], 'server':1 if i%2 else 2,
                     'point_winner':1 if winner==1 and i%3 else (-1 if winner==0 and i%3==0 else 0),
                     'win_probability_p1':0.99})  # must not become a feature
    return {'match':{'player1_name':'A','player2_name':'B','winner':winner+1,'date':f'2026-01-{1+int(mid):02d}'},
            'meta':{'coverage':'point'},'tape':rows}


def test_builder_excludes_vendor_probability_and_is_causal():
    b=LiveSnapshotBuilderV47(max_snapshots_per_match=20,prior_provider=lambda a,b:.6)
    snaps=b.build_match('1',make_tape('1',1))
    assert snaps
    assert 'win_probability_p1' not in snaps[0].features
    assert snaps[0].features['prior_logit'] > 0


def test_train_and_reload(tmp_path):
    b=LiveSnapshotBuilderV47(max_snapshots_per_match=20,prior_provider=lambda a,b:.6)
    matches=[(str(i),make_tape(str(i),i%2)) for i in range(20)]
    snaps=b.build(matches)
    path=tmp_path/'live.joblib'
    model,metrics=train_live_model(snaps,path)
    assert path.exists()
    assert metrics['test']['n']>0
    adapter=LiveMLAdapterV47(path)
    p=adapter.predict(.6,make_tape('1',1)['tape'][5])
    assert 0 < p < 1
