from vika_engine.ratings.player_state import PlayerStateStore


def test_get_matches_reordered_provider_name():
    store=PlayerStateStore()
    expected=store._p('Coco Gauff')

    assert store.get('Gauff, Coco') is expected


def test_get_does_not_guess_ambiguous_normalized_names():
    store=PlayerStateStore()
    store._p('Alex Lee')
    store._p('Lee Alex')

    assert store.get('Lee, Alex') is None
