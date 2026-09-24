from preflight.pathmatch import canonical_prefix, path_prefix_matches


def test_canonical_prefix_normalizes_separators_and_trailing_slashes():
    assert canonical_prefix("src") == "src"
    assert canonical_prefix("src/") == "src"
    assert canonical_prefix("src\\") == "src"
    assert canonical_prefix("src/payment/") == "src/payment"
    assert canonical_prefix("src\\payment\\") == "src/payment"


def test_path_prefix_is_path_segment_aware():
    assert path_prefix_matches("src/app.py", "src") is True
    assert path_prefix_matches("src2/app.py", "src") is False
    assert path_prefix_matches("src/app.py", "src/") is True
    assert path_prefix_matches("src/app.py", "src\\") is True
