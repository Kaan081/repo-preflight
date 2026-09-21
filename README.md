Repo Preflight is a read-only Git CLI that turns a branch diff into an integration-focused report: ownership, technical risk, governance gaps, required checks, and a short manual-review list.

It is designed for small teams and solo developers who want a repeatable pre-merge/pre-integration check without giving a tool permission to modify the repository.

What it does

Repo Preflight can:

compare a base revision against HEAD or another fetched revision

classify changed files using exact names, path prefixes, and extensions

resolve repository ownership with prefix and path_exact rules

flag ownership gaps and ownership-boundary crossings

separate technical risk from governance status

emit required verification checks

produce a short manual-review list instead of treating every changed file equally

warn when the working tree is dirty

output human-readable text or deterministic JSON

It does not merge, checkout, commit, delete, modify, or automatically approve repository changes.

Example

=== Repository Preflight ===
Current branch: dev
Base: dev
Head: origin/feature/environment-pass
Repository state: CLEAN

Technical risk: MEDIUM
Governance: PASS

Changed files: 14
High risk: 0
Medium risk: 14
Low risk: 0
Manual reviews: 1
Git status mix: A=13, M=1
File types: asset=13, map=1
Owners: Art=13, Shared=1

Required checks:
- asset verification
- map integration verification

Manual review:
- Content/Maps/Level_Art.umap

Governance issues:
- None

Requirements

Python 3.10+

Git available on PATH

Runtime dependencies: none outside the Python standard library.

Install for development

Clone the repository and run:

python -m pip install -e .

Then verify the CLI:

preflight --help

For test dependencies:

python -m pip install -e '.[dev]'
python -m pytest -q

Minimal configuration

Create .preflight.json in your repository root:

{
  "ownership": [
    {
      "match": "prefix",
      "path": "src/",
      "owner": "Backend"
    },
    {
      "match": "path_exact",
      "path": "Dockerfile",
      "owner": "Platform"
    }
  ]
}

ownership is required. Governance thresholds and file-type rules have defaults.

Ownership matching

prefix owns a path subtree:

{"match": "prefix", "path": "src/payment/", "owner": "Payments"}

path_exact owns one exact repository-relative path:

{"match": "path_exact", "path": "Dockerfile", "owner": "Platform"}

When several ownership rules match, the most specific rule wins. Exact-path matches win equivalent prefix matches.

An unmatched path becomes Unknown. This does not stop the analysis; it is reported as an ownership governance gap.

Run

Compare the current checked-out revision against dev:

preflight --base dev

Analyze a fetched branch without checking it out:

preflight --base dev --head origin/feature/my-change

Use a config outside the repository:

preflight --base main --config /path/to/preflight.json

Machine-readable output:

preflight --base main --json

If you redirect JSON into a file inside the inspected repository, the shell creates that file before Repo Preflight starts, so the working tree can correctly appear as DIRTY. Redirect outside the repository if you want an unchanged worktree state.

Exit codes

Code

Meaning

0

Analysis completed successfully, even if risk/governance warnings were found

2

Configuration error

3

Git/repository/revision error

4

Known Repo Preflight domain error

HIGH technical risk, CRITICAL governance, or a dirty worktree do not block by default. Repo Preflight is advisory in the current release.

Security model

Repo Preflight is intentionally read-only.

The CLI:

never uses shell=True

passes Git arguments as an argument list

validates user-supplied Git revisions before invoking Git

uses a Git command timeout

checks Git return codes and stderr

disables external diff and textconv helpers for diff inspection

disables fsmonitor hooks for worktree status inspection

escapes terminal control characters from repository/config-derived display text

does not execute commands from .preflight.json

does not require API keys, credentials, or network access

See SECURITY.md for vulnerability reporting guidance.

File classification

Default semantic types include:

source

asset

map

build_config

fallback other

Classification precedence is:

exact filename

most-specific path prefix

extension

other

Custom file_types replace the default classification rules.

Governance defaults

If omitted, governance uses:

{
  "critical_escalation": true,
  "critical_unknown_count": 5,
  "critical_unknown_ratio": 0.25
}

Ownership gaps produce ATTENTION until the configured count/ratio threshold is crossed. A confirmed ownership-boundary crossing is CRITICAL.

Project status

Current release: 0.1.3

The project is intentionally conservative: it reports and prioritizes integration signals instead of automatically merging or blocking changes.

Known scope limits include detached-HEAD handling and richer language/framework-specific semantic analysis.

Contributing

Issues, tests, rule improvements, documentation changes, and focused pull requests are welcome. See CONTRIBUTING.md.

License

MIT License. See LICENSE.
