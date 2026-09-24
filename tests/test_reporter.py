import json

from preflight.reporter import print_json_report, print_report, terminal_safe


def test_terminal_safe_escapes_control_characters():
    value = "evil\x1b[31m\nfile\tname"
    result = terminal_safe(value)

    assert "\x1b" not in result
    assert "\n" not in result
    assert "\t" not in result
    assert result == r"evil\x1b[31m\nfile\tname"


def _report_with_topology(ff_eligible=True):
    return {
        "branch": "feature/x",
        "base": "main",
        "head": "HEAD",
        "repository_state": "CLEAN",
        "technical_risk": "LOW",
        "governance_status": "PASS",
        "summary": {
            "total_changes": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "manual_review_count": 0,
            "manual_review_files": [],
            "required_checks": [],
            "owners": [],
            "owner_counts": {},
            "status_counts": {},
            "file_type_counts": {},
            "governance_issue_count": 0,
        },
        "changes": [],
        "topology": {
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "merge_base": "a" * 40,
            "behind": 0 if ff_eligible else 2,
            "ahead": 3,
            "relationship": "LINEAR" if ff_eligible else "DIVERGED",
            "ff_eligible": ff_eligible,
        },
    }


def test_print_report_includes_topology_section(capsys):
    print_report(_report_with_topology())
    output = capsys.readouterr().out
    assert "Topology:" in output
    assert f"Base SHA: {'a' * 40}" in output
    assert f"Head SHA: {'b' * 40}" in output
    assert f"Merge base: {'a' * 40}" in output
    assert "Behind: 0" in output
    assert "Ahead: 3" in output
    assert "Relationship: LINEAR" in output
    assert "FF eligible: YES" in output


def test_print_json_report_uses_boolean_ff_eligible(capsys):
    print_json_report(_report_with_topology(ff_eligible=False))
    raw = capsys.readouterr().out
    payload = json.loads(raw)
    assert payload["topology"]["ff_eligible"] is False
    assert "YES" not in raw
    assert "NO" not in json.dumps(payload["topology"])
