import json, gzip
from pathlib import Path
from vika_engine.training.history_tape import normalize_tape, write_jsonl
from vika_engine.training.live_model_v47 import LiveSnapshotBuilderV47


def sample():
    return {'match':{'id':'m1','date':'2025-01-02','player1_name':'A','player2_name':'B','winner':1},
            'tape':[{'seq':1,'server':1,'point_winner':1,'games':[0,0]}, {'seq':2,'server':1,'point_winner':2,'games':[0,0]}, {'seq':3,'server':2,'point_winner':1,'games':[1,0]}],
            'meta':{'point_source':'observed_live'}}

def test_normalize_no_match_winner_leakage():
    x=normalize_tape(sample(),'livetennis_observed')
    assert x and x['match']['winner']==1
    assert x['tape'][0]['point_winner']==1
    assert x['meta']['source']=='livetennis_observed'

def test_builder_uses_causal_point_winner():
    x=normalize_tape(sample(),'livetennis_observed')
    s=LiveSnapshotBuilderV47(max_snapshots_per_match=10).build_match('m1',x)
    assert len(s)==3
    assert s[0].features['momentum_sample']==1
    assert s[1].features['momentum_sample']==2
    assert s[2].features['momentum_sample']==3
    assert all(v.target==1 for v in s)

def test_jsonl_roundtrip(tmp_path):
    p=tmp_path/'x.jsonl'
    write_jsonl([sample()],p)
    assert json.loads(p.read_text())['match']['id']=='m1'
