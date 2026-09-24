import json
import os
import subprocess
import sys
from pathlib import Path

from preflight.git import get_git_topology


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


def commit_file(repo, relative, content, message):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def current_branch(repo):
    return git(repo, "branch", "--show-current").stdout.strip()


def write_config(repo):
    config_data = {
        "ownership": [
            {"match": "prefix", "path": "src/", "owner": "Backend"},
        ]
    }
    config_path = repo / ".preflight.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    return config_path


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


def test_topology_same(tmp_path):
    repo = init_repo(tmp_path)
    sha = commit_file(repo, "src/app.py", "v1\n", "initial")

    topology = get_git_topology(sha, sha, cwd=repo)

    assert topology["base_sha"] == sha
    assert topology["head_sha"] == sha
    assert topology["merge_base"] == sha
    assert topology["behind"] == 0
    assert topology["ahead"] == 0
    assert topology["relationship"] == "SAME"
    assert topology["ff_eligible"] is True


def test_topology_linear(tmp_path):
    repo = init_repo(tmp_path)
    base_sha = commit_file(repo, "src/app.py", "v1\n", "base")
    head_sha = commit_file(repo, "src/app.py", "v2\n", "feature")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)

    assert topology["base_sha"] == base_sha
    assert topology["head_sha"] == head_sha
    assert topology["merge_base"] == base_sha
    assert topology["behind"] == 0
    assert topology["ahead"] > 0
    assert topology["relationship"] == "LINEAR"
    assert topology["ff_eligible"] is True


def test_topology_head_behind(tmp_path):
    repo = init_repo(tmp_path)
    head_sha = commit_file(repo, "src/app.py", "v1\n", "older")
    base_sha = commit_file(repo, "src/app.py", "v2\n", "newer-on-base")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)

    assert topology["base_sha"] == base_sha
    assert topology["head_sha"] == head_sha
    assert topology["merge_base"] == head_sha
    assert topology["behind"] > 0
    assert topology["ahead"] == 0
    assert topology["relationship"] == "HEAD_BEHIND"
    assert topology["ff_eligible"] is False


def test_topology_diverged(tmp_path):
    repo = init_repo(tmp_path)
    root_sha = commit_file(repo, "src/app.py", "v1\n", "root")
    base_branch = current_branch(repo)

    git(repo, "checkout", "-b", "feature/diverged")
    head_sha = commit_file(repo, "src/app.py", "feature\n", "feature-only")

    git(repo, "checkout", base_branch)
    base_sha = commit_file(repo, "src/app.py", "base\n", "base-only")

    topology = get_git_topology(base_sha, head_sha, cwd=repo)

    assert topology["base_sha"] == base_sha
    assert topology["head_sha"] == head_sha
    assert topology["merge_base"] == root_sha
    assert topology["behind"] > 0
    assert topology["ahead"] > 0
    assert topology["relationship"] == "DIVERGED"
    assert topology["ff_eligible"] is False


def test_cli_json_includes_topology(tmp_path):
    repo = init_repo(tmp_path)
    base_sha = commit_file(repo, "src/app.py", "v1\n", "base")
    config_path = write_config(repo)
    git(repo, "add", ".preflight.json")
    git(repo, "commit", "-m", "config")
    git(repo, "checkout", "-b", "feature/json-topology")
    commit_file(repo, "src/app.py", "v2\n", "feature")

    result = run_preflight_json(repo, config_path, "--base", base_sha)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    topology = report["topology"]
    assert topology["base_sha"] == base_sha
    assert topology["head_sha"]
    assert topology["merge_base"] == base_sha
    assert topology["behind"] == 0
    assert topology["ahead"] > 0
    assert topology["relationship"] == "LINEAR"
    assert topology["ff_eligible"] is True
    assert isinstance(topology["ff_eligible"], bool)


def test_cli_explicit_head_without_checkout(tmp_path):
    repo = init_repo(tmp_path)
    commit_file(repo, "src/app.py", "v1\n", "base")
    config_path = write_config(repo)
    git(repo, "add", ".preflight.json")
    git(repo, "commit", "-m", "config")
    base_branch = current_branch(repo)

    git(repo, "checkout", "-b", "feature/explicit-head")
    feature_sha = commit_file(repo, "src/app.py", "v2\n", "feature")
    git(repo, "checkout", base_branch)

    result = run_preflight_json(
        repo,
        config_path,
        "--base",
        base_branch,
        "--head",
        feature_sha,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert current_branch(repo) == base_branch
    assert report["branch"] == base_branch
    assert report["head"] == feature_sha
    topology = report["topology"]
    assert topology["base_sha"] == git(repo, "rev-parse", base_branch).stdout.strip()
    assert topology["head_sha"] == feature_sha
    assert topology["merge_base"] == topology["base_sha"]
    assert topology["relationship"] == "LINEAR"
    assert topology["behind"] == 0
    assert topology["ahead"] > 0
    assert topology["ff_eligible"] is True
    assert report["summary"]["total_changes"] >= 1
