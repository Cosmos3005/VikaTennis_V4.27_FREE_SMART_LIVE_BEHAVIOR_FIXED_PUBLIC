from vika_engine.live.model import LiveWinModel

def test_live_prior_is_respected_early():
    m=LiveWinModel(.65)
    f=m.from_frame(.65, {'score':{'sets':[0,0],'games':[0,0]}, 'win_probability_p1':None})
    r=m.predict(f)
    assert 0.60 < r['p1_win'] < 0.70

def test_live_set_lead_moves_probability():
    m=LiveWinModel(.65)
    f=m.from_frame(.65, {'score':{'sets':[1,0],'games':[4,2]}, 'win_probability_p1':None})
    r=m.predict(f)
    assert r['p1_win'] > .70

def test_api_probability_is_blended():
    m=LiveWinModel(.65)
    f=m.from_frame(.65, {'score':{'sets':[0,1],'games':[2,4]}, 'win_probability_p1':.20})
    r=m.predict(f)
    assert r['p1_win'] < .5
