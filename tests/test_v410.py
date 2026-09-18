from datetime import date,timedelta
from vika_engine.training.walk_forward_live import run_walk_forward,aggregate
from vika_engine.training.live_model_v47 import Snapshot

def make_snaps(n=300):
    out=[];start=date(2022,1,1)
    for i in range(n):
        d=start+timedelta(days=i*8);y=i%2
        for j in range(4):
            out.append(Snapshot(str(i),str(d),j+1,y,'point',{'prior_logit':.2 if y else -.2,'sets_diff':1 if y and j>=2 else (-1 if not y and j>=2 else 0),'games_diff':2 if y else -2,'games_total':4+j,'set_margin_abs':1 if j>=2 else 0,'server_p1':1,'point_diff':1 if y else -1,'point_total':j+1,'elapsed_minutes':j*5,'seq_log':j,'momentum_ewma':.4 if y else -.4,'momentum_sample':j,'momentum_pressure':.2 if y else -.2}))
    return out

def test_walk_forward():
    r=aggregate(run_walk_forward(make_snaps(),validation_days=90));assert r['total_folds']==3;assert r['successful_folds']>=1;assert r['champion'] in r['models']
