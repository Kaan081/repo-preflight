import subprocess

from .errors import GitError


GIT_TIMEOUT_SECONDS = 15


def run_git(args, cwd=None):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise GitError("Git executable was not found") from error
    except subprocess.TimeoutExpired as error:
        raise GitError("Git command timed out") from error

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise GitError(message)

    return result.stdout


def ensure_git_repository(cwd=None):
    value = run_git(["rev-parse", "--is-inside-work-tree"], cwd=cwd).strip()
    if value != "true":
        raise GitError("Current directory is not a Git repository")


def get_current_branch(cwd=None):
    branch = run_git(["branch", "--show-current"], cwd=cwd).strip()
    if not branch:
        raise GitError("Could not determine current branch (detached HEAD is not supported in v0.1)")
    return branch


def validate_revision_argument(revision):
    if not isinstance(revision, str) or not revision:
        raise GitError("Git revision must be a non-empty string")
    if revision.startswith("-") or "\0" in revision or "\n" in revision or "\r" in revision:
        raise GitError(f"Unsafe Git revision argument: {revision!r}")


def ensure_revision_exists(revision, cwd=None):
    validate_revision_argument(revision)
    try:
        run_git(["rev-parse", "--verify", "--quiet", revision], cwd=cwd)
    except GitError as error:
        raise GitError(f"Git revision does not exist: {revision}") from error


def get_diff_name_status(base_branch, head_revision="HEAD", cwd=None):
    validate_revision_argument(base_branch)
    validate_revision_argument(head_revision)
    return run_git(
        [
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--no-ext-diff",
            "--no-textconv",
            f"{base_branch}...{head_revision}",
        ],
        cwd=cwd,
    )


def get_worktree_status(cwd=None):
    # Disable repo/user-configured fsmonitor hooks for read-only inspection.
    return run_git(["-c", "core.fsmonitor=false", "status", "--porcelain"], cwd=cwd)


def is_worktree_dirty(cwd=None):
    return bool(get_worktree_status(cwd=cwd).strip())


def parse_git_diff(raw):
    tokens = raw.split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()

    changes = []
    index = 0

    while index < len(tokens):
        status_token = tokens[index]
        index += 1

        if not status_token:
            raise GitError("Malformed Git diff record: empty status")

        git_status = status_token[0]

        if git_status in ("R", "C"):
            if index + 1 >= len(tokens):
                raise GitError("Malformed Git rename/copy record")

            old_path = tokens[index]
            new_path = tokens[index + 1]
            index += 2

            score_text = status_token[1:]
            similarity = int(score_text) if score_text.isdigit() else None

            changes.append(
                {
                    "git_status": git_status,
                    "similarity": similarity,
                    "old_path": old_path,
                    "path": new_path,
                }
            )
            continue

        if index >= len(tokens):
            raise GitError("Malformed Git diff record")

        path = tokens[index]
        index += 1
        changes.append({"git_status": git_status, "path": path})

    return changes
