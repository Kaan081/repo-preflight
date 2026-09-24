import json
import os
import subprocess
import sys
from pathlib import Path

from preflight.collisions import build_collision_report
from preflight.config import normalize_config
from preflight.git import get_collision_paths, get_git_topology


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def init_repo(tmp_path, name="repo"):
    repo = tmp_path / name
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Preflight Test")
    return repo


def write_files(repo, mapping):
    for relative, content in mapping.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def current_branch(repo):
    return git(repo, "branch", "--show-current").stdout.strip()


def write_config(repo):
    config_data = {
        "ownership": [
            {"match": "prefix", "path": "src/", "owner": "Backend"},
            {"match": "prefix", "path": "Content/", "owner": "Art"},
        ]
    }
    config_path = repo / ".preflight.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    return config_path


def commit_all(repo, message):
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def create_diverged_repo(tmp_path, shared, base_edits, head_edits):
    repo = init_repo(tmp_path)
    write_files(repo, shared)
    config_path = write_config(repo)
    commit_all(repo, "shared")
    base_branch = current_branch(repo)

    git(repo, "checkout", "-b", "feature/collision")
    write_files(repo, head_edits)
    head_sha = commit_all(repo, "head-side")

    git(repo, "checkout", base_branch)
    write_files(repo, base_edits)
    base_sha = commit_all(repo, "base-side")
    return repo, base_branch, base_sha, head_sha, config_path


def run_preflight_json(repo, config_path, *extra_args):
    env = os.environ.copy()
    src_path = str((Path(__file__).parents[1] / "src").resolve())
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "preflight",
            "--config",
            str(config_path),
            "--json",
            *extra_args,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def collision_paths(repo, base_sha, head_sha):
    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    return get_collision_paths(topology, cwd=repo)


def test_diverged_different_files_have_no_collisions(tmp_path):
    repo, _, base_sha, head_sha, _ = create_diverged_repo(
        tmp_path,
        shared={"src/app.py": "shared-app\n", "src/other.py": "shared-other\n"},
        base_edits={"src/other.py": "base-other\n"},
        head_edits={"src/app.py": "head-app\n"},
    )
    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    assert topology["relationship"] == "DIVERGED"
    assert collision_paths(repo, base_sha, head_sha) == set()


def test_diverged_same_source_file_is_a_collision(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={"src/app.py": "shared\n"},
        base_edits={"src/app.py": "base\n"},
        head_edits={"src/app.py": "head\n"},
    )
    paths = collision_paths(repo, base_sha, head_sha)
    assert paths == {"src/app.py"}

    config = normalize_config(json.loads(config_path.read_text(encoding="utf-8")))
    report = build_collision_report(paths, config["file_types"])
    assert report["count"] == 1
    assert report["binary_sensitive_count"] == 0
    assert report["files"] == [
        {"path": "src/app.py", "file_type": "source", "binary_sensitive": False}
    ]


def test_diverged_same_uasset_is_binary_sensitive(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={"Content/Thing.uasset": "shared\n"},
        base_edits={"Content/Thing.uasset": "base\n"},
        head_edits={"Content/Thing.uasset": "head\n"},
    )
    paths = collision_paths(repo, base_sha, head_sha)
    assert paths == {"Content/Thing.uasset"}

    config = normalize_config(json.loads(config_path.read_text(encoding="utf-8")))
    report = build_collision_report(paths, config["file_types"])
    assert report["count"] == 1
    assert report["binary_sensitive_count"] == 1
    assert report["files"][0]["file_type"] == "asset"
    assert report["files"][0]["binary_sensitive"] is True


def test_diverged_same_umap_is_binary_sensitive(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={"Content/Maps/Test.umap": "shared\n"},
        base_edits={"Content/Maps/Test.umap": "base\n"},
        head_edits={"Content/Maps/Test.umap": "head\n"},
    )
    paths = collision_paths(repo, base_sha, head_sha)
    assert paths == {"Content/Maps/Test.umap"}

    config = normalize_config(json.loads(config_path.read_text(encoding="utf-8")))
    report = build_collision_report(paths, config["file_types"])
    assert report["count"] == 1
    assert report["files"][0]["file_type"] == "map"
    assert report["files"][0]["binary_sensitive"] is True


def test_multiple_collisions_are_sorted_with_correct_counts(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={
            "src/z.py": "shared-z\n",
            "src/a.py": "shared-a\n",
            "Content/Thing.uasset": "shared-asset\n",
        },
        base_edits={
            "src/z.py": "base-z\n",
            "src/a.py": "base-a\n",
            "Content/Thing.uasset": "base-asset\n",
        },
        head_edits={
            "src/z.py": "head-z\n",
            "src/a.py": "head-a\n",
            "Content/Thing.uasset": "head-asset\n",
        },
    )
    config = normalize_config(json.loads(config_path.read_text(encoding="utf-8")))
    report = build_collision_report(
        collision_paths(repo, base_sha, head_sha),
        config["file_types"],
    )
    assert report["count"] == 3
    assert report["count"] == len(report["files"])
    assert report["binary_sensitive_count"] == 1
    assert [item["path"] for item in report["files"]] == [
        "Content/Thing.uasset",
        "src/a.py",
        "src/z.py",
    ]
    assert report["files"][0]["binary_sensitive"] is True
    assert report["files"][1]["binary_sensitive"] is False
    assert report["files"][2]["binary_sensitive"] is False


def test_linear_topology_has_no_collisions(tmp_path):
    repo = init_repo(tmp_path)
    write_files(repo, {"src/app.py": "v1\n"})
    config_path = write_config(repo)
    base_sha = commit_all(repo, "base")
    write_files(repo, {"src/app.py": "v2\n"})
    head_sha = commit_all(repo, "linear-head")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    assert topology["relationship"] == "LINEAR"
    assert collision_paths(repo, base_sha, head_sha) == set()

    result = run_preflight_json(repo, config_path, "--base", base_sha)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["topology"]["relationship"] == "LINEAR"
    assert report["collisions"]["count"] == 0
    assert report["collisions"]["binary_sensitive_count"] == 0
    assert report["collisions"]["files"] == []


def test_explicit_head_without_checkout_detects_collisions(tmp_path):
    repo, base_branch, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={"src/app.py": "shared\n"},
        base_edits={"src/app.py": "base\n"},
        head_edits={"src/app.py": "head\n"},
    )
    assert current_branch(repo) == base_branch

    result = run_preflight_json(
        repo,
        config_path,
        "--base",
        base_sha,
        "--head",
        head_sha,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert current_branch(repo) == base_branch
    assert report["branch"] == base_branch
    assert report["head"] == head_sha
    assert report["topology"]["relationship"] == "DIVERGED"
    assert report["collisions"]["count"] == 1
    assert report["collisions"]["files"][0]["path"] == "src/app.py"


def test_cli_json_collision_schema_uses_real_booleans(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={
            "src/app.py": "shared-src\n",
            "Content/Thing.uasset": "shared-asset\n",
        },
        base_edits={
            "src/app.py": "base-src\n",
            "Content/Thing.uasset": "base-asset\n",
        },
        head_edits={
            "src/app.py": "head-src\n",
            "Content/Thing.uasset": "head-asset\n",
        },
    )
    result = run_preflight_json(
        repo,
        config_path,
        "--base",
        base_sha,
        "--head",
        head_sha,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    collisions = report["collisions"]
    assert collisions["count"] == 2
    assert collisions["count"] == len(collisions["files"])
    assert collisions["binary_sensitive_count"] == 1
    assert collisions["binary_sensitive_count"] == sum(
        1 for item in collisions["files"] if item["binary_sensitive"]
    )
    assert [item["path"] for item in collisions["files"]] == [
        "Content/Thing.uasset",
        "src/app.py",
    ]
    assert collisions["files"][0]["binary_sensitive"] is True
    assert collisions["files"][1]["binary_sensitive"] is False
    assert isinstance(collisions["files"][0]["binary_sensitive"], bool)
    assert isinstance(collisions["files"][1]["binary_sensitive"], bool)
    assert "YES" not in json.dumps(collisions)
    assert "NO" not in json.dumps(collisions)
    assert report["technical_risk"] in {"LOW", "MEDIUM", "HIGH"}
    assert report["governance_status"] in {"PASS", "ATTENTION", "CRITICAL"}


def test_add_add_same_path_on_diverged_branches_is_a_collision(tmp_path):
    repo, _, base_sha, head_sha, config_path = create_diverged_repo(
        tmp_path,
        shared={"src/keep.py": "keep\n"},
        base_edits={"src/new.py": "base-new\n"},
        head_edits={"src/new.py": "head-new\n"},
    )
    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    assert topology["relationship"] == "DIVERGED"

    paths = collision_paths(repo, base_sha, head_sha)
    assert "src/new.py" in paths

    config = normalize_config(json.loads(config_path.read_text(encoding="utf-8")))
    report = build_collision_report(paths, config["file_types"])
    assert report["count"] == 1
    assert report["files"][0]["path"] == "src/new.py"


def test_delete_modify_same_path_on_diverged_branches_is_a_collision(tmp_path):
    repo = init_repo(tmp_path)
    write_files(repo, {"src/app.py": "shared\n"})
    write_config(repo)
    commit_all(repo, "shared")
    base_branch = current_branch(repo)

    git(repo, "checkout", "-b", "feature/collision")
    write_files(repo, {"src/app.py": "head-modified\n"})
    head_sha = commit_all(repo, "head-modifies")

    git(repo, "checkout", base_branch)
    git(repo, "rm", "src/app.py")
    base_sha = commit_all(repo, "base-deletes")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    assert topology["relationship"] == "DIVERGED"
    assert collision_paths(repo, base_sha, head_sha) == {"src/app.py"}


def test_rename_collisions_are_path_string_overlap_not_identity_tracking(tmp_path):
    """Renames are path-string overlap only; --no-renames is the contract.

    Head renames src/old.py -> src/renamed.py. Base modifies src/old.py and
    does not touch src/renamed.py. A rename-identity detector might treat
    those as the same file. This tool reports only the overlapping path
    string src/old.py (deleted on one side, modified on the other) and must
    not report src/renamed.py.
    """
    repo = init_repo(tmp_path)
    write_files(repo, {"src/old.py": "shared\n"})
    write_config(repo)
    commit_all(repo, "shared")
    base_branch = current_branch(repo)

    git(repo, "checkout", "-b", "feature/collision")
    git(repo, "mv", "src/old.py", "src/renamed.py")
    head_sha = commit_all(repo, "head-renames")

    git(repo, "checkout", base_branch)
    write_files(repo, {"src/old.py": "base-modified\n"})
    base_sha = commit_all(repo, "base-modifies-old-path")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)
    assert topology["relationship"] == "DIVERGED"

    paths = collision_paths(repo, base_sha, head_sha)
    assert paths == {"src/old.py"}
    assert "src/renamed.py" not in paths
