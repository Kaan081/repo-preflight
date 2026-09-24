import argparse
import sys

from .analyzer import analyze_change
from .collisions import build_collision_report
from .config import load_config
from .errors import ConfigError, GitError, PreflightError
from .git import (
    ensure_git_repository,
    ensure_revision_exists,
    get_collision_paths,
    get_current_branch,
    get_diff_name_status,
    get_git_topology,
    is_worktree_dirty,
    parse_git_diff,
)
from .pipeline import build_change_context
from .report import build_report
from .reporter import print_json_report, print_report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Analyze Git changes before integration"
    )
    parser.add_argument("--base", default="dev", help="Base branch/revision to compare against")
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head branch/revision to analyze without checking it out",
    )
    parser.add_argument("--config", default=".preflight.json", help="Path to preflight config")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    return parser.parse_args(argv)


def run(argv=None, cwd=None):
    args = parse_args(argv)
    config = load_config(args.config)

    ensure_git_repository(cwd=cwd)
    ensure_revision_exists(args.base, cwd=cwd)
    ensure_revision_exists(args.head, cwd=cwd)
    branch = get_current_branch(cwd=cwd)
    dirty = is_worktree_dirty(cwd=cwd)
    topology = get_git_topology(args.base, args.head, cwd=cwd)
    collisions = build_collision_report(
        get_collision_paths(topology, cwd=cwd),
        config["file_types"],
    )

    raw_changes = parse_git_diff(
        get_diff_name_status(args.base, head_revision=args.head, cwd=cwd)
    )
    analyzed_changes = []

    for raw_change in raw_changes:
        context = build_change_context(raw_change, config)
        analyzed_changes.append(analyze_change(context))

    report = build_report(
        branch,
        args.base,
        analyzed_changes,
        config["governance"],
        worktree_dirty=dirty,
        head_revision=args.head,
        topology=topology,
        collisions=collisions,
    )

    if args.json:
        print_json_report(report)
    else:
        print_report(report)

    return report


def main():
    try:
        run()
    except ConfigError as error:
        print(f"CONFIG ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    except GitError as error:
        print(f"GIT ERROR: {error}", file=sys.stderr)
        raise SystemExit(3)
    except PreflightError as error:
        print(f"PREFLIGHT ERROR: {error}", file=sys.stderr)
        raise SystemExit(4)
