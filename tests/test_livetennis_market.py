from vika_engine.auto_live import extract_livetennis_market_probability


def test_extracts_latest_live_tennis_match_winner_midpoints():
    frame = {
        "market": {
            "status": "active",
            "prices": [
                {"side": 1, "mid": 0.68, "timestamp": "2026-09-23T12:02:00Z"},
                {"side": 1, "mid": 0.66, "timestamp": "2026-09-23T12:01:00Z"},
                {"side": 2, "mid": 0.34, "timestamp": "2026-09-23T12:02:00Z"},
            ],
        }
    }

    result = extract_livetennis_market_probability(frame)

    assert result == {
        "p1": 0.68,
        "p2": 0.34,
        "timestamp": "2026-09-23T12:02:00Z",
        "status": "active",
    }


def test_closed_or_incomplete_market_is_not_used():
    assert extract_livetennis_market_probability({"market": {
        "status": "resolved",
        "prices": [{"side": 1, "mid": 0.8}, {"side": 2, "mid": 0.2}],
    }}) is None
    assert extract_livetennis_market_probability({"market": {
        "status": "active",
        "prices": [{"side": 1, "mid": 0.8}, {"side": 2, "mid": 1.43}],
    }}) is None
