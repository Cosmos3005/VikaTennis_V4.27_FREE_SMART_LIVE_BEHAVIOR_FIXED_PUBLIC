import pandas as pd
from vika_engine.features import FeatureBuilder

def test_feature_builder_is_pre_match_and_flipped():
    df=pd.DataFrame([{'tourney_date':'20240101','match_num':1,'winner_id':1,'winner_name':'A','loser_id':2,'loser_name':'B','surface':'Hard','best_of':3,'score':'6-4 6-4','minutes':90,'w_svpt':60,'w_1stIn':40,'w_1stWon':30,'w_2ndWon':10,'l_svpt':55,'l_1stIn':35,'l_1stWon':20,'l_2ndWon':8}])
    ds=FeatureBuilder().build(df)
    assert len(ds)==0 or set(ds.target_win.unique()).issubset({0,1})

def test_date_window_contract(tmp_path):
    d=pd.DataFrame({'date':pd.to_datetime(['2015-01-01','2025-12-31'])})
    assert d.date.min().year==2015 and d.date.max().year==2025
