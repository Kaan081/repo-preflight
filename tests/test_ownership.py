from preflight.ownership import get_owner, rule_matches


def test_specific_prefix_wins():
    rules = [
        {"path": "src/", "owner": "Backend"},
        {"path": "src/payment/", "owner": "Payments"},
    ]
    assert get_owner("src/payment/checkout.py", rules) == "Payments"


def test_unmatched_path_is_unknown():
    rules = [{"path": "src/", "owner": "Backend"}]
    assert get_owner("scripts/deploy.py", rules) == "Unknown"


def test_default_owner_is_used():
    rules = [{"path": "src/", "owner": "Backend"}]
    assert get_owner("scripts/deploy.py", rules, "Core") == "Core"


def test_path_exact_does_not_match_similar_name():
    rule = {"match": "path_exact", "path": "Dockerfile", "owner": "Platform"}
    assert rule_matches("Dockerfile", rule) is True
    assert rule_matches("Dockerfile.backup", rule) is False
    assert rule_matches("infra/Dockerfile", rule) is False


def test_path_exact_beats_equal_length_prefix():
    rules = [
        {"match": "prefix", "path": "src/", "owner": "General"},
        {"match": "path_exact", "path": "src/", "owner": "Exact"},
    ]
    assert get_owner("src/", rules) == "Exact"


def test_prefix_is_path_segment_aware():
    rule = {"match": "prefix", "path": "src", "owner": "Backend"}

    assert rule_matches("src", rule) is True
    assert rule_matches("src/app.py", rule) is True
    assert rule_matches("src2/app.py", rule) is False


def test_prefix_normalizes_windows_separators():
    rule = {"match": "prefix", "path": "src\\payment", "owner": "Payments"}

    assert rule_matches("src/payment/checkout.py", rule) is True
