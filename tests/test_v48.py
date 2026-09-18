import gzip, json
from pathlib import Path

def test_pipeline_module_imports():
    import scripts_v48_pipeline as p
    assert p.iso_date('2024-01-02T00:00:00Z').isoformat()=='2024-01-02'

def test_filter_last_five_year_window(tmp_path):
    src=tmp_path/'x.jsonl.gz'
    objs=[
      {'match':{'date':'2021-09-07','tour':'atp','draw':'singles','winner':1},'tape':[{'sets':[0,0]}], 'meta':{'coverage':'complete'}},
      {'match':{'date':'2021-09-08','tour':'atp','draw':'singles','winner':1},'tape':[{'sets':[0,0]}], 'meta':{'coverage':'complete'}},
      {'match':{'date':'2024-01-01','tour':'wta','draw':'singles','winner':2},'tape':[{'sets':[0,0]}], 'meta':{'coverage':'complete'}},
    ]
    with gzip.open(src,'wt',encoding='utf-8') as f:
      for x in objs:f.write(json.dumps(x)+'\n')
    from scripts_v48_pipeline import write_filtered
    out=tmp_path/'out.jsonl'; n,k=write_filtered([src],out,__import__('datetime').date(2021,9,8),__import__('datetime').date(2026,9,8),'mixed',tours=('atp','wta'),singles_only=True,min_coverage=True)
    assert n==3 and k==2
    assert sum(1 for _ in open(out))==2

def test_champion_metrics_and_ranking(tmp_path):
    from vika_engine.training.live_model_v47 import Snapshot
    from vika_engine.training.champion_live import metrics, pre_match_probs
    snaps=[]
    for i,y in enumerate([0,1,0,1]):
        snaps.append(Snapshot(str(i),'2025-01-01',i+1,y,'complete',{'prior_logit':(-1 if y==0 else 1)}))
    p=pre_match_probs(snaps)
    m=metrics(snaps,p)
    assert m['n_snapshots']==4 and m['n_matches']==4
    assert m['brier'] < .25
