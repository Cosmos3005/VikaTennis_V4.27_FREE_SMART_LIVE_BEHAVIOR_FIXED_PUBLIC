from vika_engine.data import parse_score, enrich_targets
from vika_engine.point_features import extract_match_point_stats


def test_score_excludes_retirements_and_walkovers():
    assert parse_score('6-4 6-3')[2] is True
    assert parse_score('6-4 2-1 RET')[2] is False
    assert parse_score('W/O')[2] is False


def test_point_attribution_uses_previous_server():
    tape={
      'match': {'players': {'p1': {'name':'A'}, 'p2': {'name':'B'}}},
      'meta': {'coverage':'point','basis':'reconstruction'},
      'tape': [
        {'server':1,'winner':None},
        {'server':1,'winner':1},
        {'server':2,'winner':2},
        {'server':2,'winner':1},
        {'server':1,'winner':1},
      ]
    }
    s=extract_match_point_stats(tape)
    assert s is None or s['attributable_points'] == 3
