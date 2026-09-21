import pytest

from preflight.errors import GitError
from preflight.git import parse_git_diff


def test_parse_modified_file():
    assert parse_git_diff("M\0src/app.py\0") == [
        {"git_status": "M", "path": "src/app.py"}
    ]


def test_parse_rename_with_similarity():
    result = parse_git_diff("R92\0src/old.py\0src/new.py\0")
    assert result == [
        {
            "git_status": "R",
            "similarity": 92,
            "old_path": "src/old.py",
            "path": "src/new.py",
        }
    ]


def test_malformed_record_fails():
    with pytest.raises(GitError, match="Malformed"):
        parse_git_diff("M\0")


def test_revision_argument_cannot_start_with_dash():
    from preflight.git import validate_revision_argument

    with pytest.raises(GitError, match="Unsafe Git revision"):
        validate_revision_argument("--help")
