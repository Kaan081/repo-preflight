from preflight.classifier import classify_file
from preflight.config import DEFAULT_FILE_TYPES


def test_source_extension():
    assert classify_file("src/app.py", DEFAULT_FILE_TYPES) == "source"


def test_workflow_path_beats_extension_or_other():
    assert classify_file(".github/workflows/ci.yml", DEFAULT_FILE_TYPES) == "build_config"


def test_dockerfile_is_build_config():
    assert classify_file("Dockerfile", DEFAULT_FILE_TYPES) == "build_config"


def test_unknown_file_is_other():
    assert classify_file("notes/random.xyz", DEFAULT_FILE_TYPES) == "other"


def test_longest_path_prefix_wins():
    file_types = {
        "general": {"names": [], "path_prefixes": ["src/"], "extensions": []},
        "security": {"names": [], "path_prefixes": ["src/security/"], "extensions": []},
    }
    assert classify_file("src/security/auth.py", file_types) == "security"
