from vika_engine.live.model import LiveWinModel
from vika_engine.live.momentum import PointMomentum


def test_momentum_ewma_moves_with_recent_points():
    m=PointMomentum(alpha=.5, window=10)
    for _ in range(5): m.update({'winner':1})
    assert m.snapshot().ewma > .8


def test_momentum_reacts_more_to_recent_than_old_points():
    m=PointMomentum(alpha=.25, window=20)
    for _ in range(8): m.update({'winner':2})
    before=m.snapshot().ewma
    for _ in range(2): m.update({'winner':1})
    after=m.snapshot().ewma
    assert after > before


def test_live_momentum_is_bounded():
    model=LiveWinModel(.5)
    for _ in range(100): model.update_point({'winner':1})
    f=model.from_frame(.5, {'score':{'sets':[0,0],'games':[0,0]}})
    r=model.predict(f)
    assert .5 < r['p1_win'] < .99
    assert r['p2_win'] == 1-r['p1_win']


def test_live_monte_carlo_returns_valid_probabilities():
    from vika_engine.live.monte_carlo import LiveMonteCarlo
    model = LiveWinModel(.62)
    f = model.from_frame(.62, {'score': {'sets':[1,0], 'games':[4,3]}})
    r = LiveMonteCarlo(seed=7).simulate(prior=.62, live_features=f, simulations=5000, best_of=3)
    assert abs(r['p1_win'] + r['p2_win'] - 1) < 1e-12
    assert 0 < r['p1_win'] < 1
    assert 0 <= r['p1_set_next'] <= 1
    assert r['simulations'] == 5000


def test_live_mc_respects_completed_set_state():
    from vika_engine.live.monte_carlo import LiveMonteCarlo
    model = LiveWinModel(.5)
    f = model.from_frame(.5, {'score': {'sets':[2,0], 'games':[0,0]}})
    r = LiveMonteCarlo(seed=7).simulate(prior=.5, live_features=f, simulations=1000, best_of=3)
    assert r['p1_win'] == 1.0
    assert r['p2_win'] == 0.0
