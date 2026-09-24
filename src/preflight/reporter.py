import json


def terminal_safe(value):
    """Escape terminal control characters in untrusted repo/config text."""
    text = str(value)
    escaped = []
    for char in text:
        code = ord(char)
        if char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        elif char.isprintable() and char != "\x1b":
            escaped.append(char)
        elif code <= 0xFF:
            escaped.append(f"\\x{code:02x}")
        elif code <= 0xFFFF:
            escaped.append(f"\\u{code:04x}")
        else:
            escaped.append(f"\\U{code:08x}")
    return "".join(escaped)


def collect_governance_issues(report):
    issues = []
    for change in report["changes"]:
        for issue in change["governance_issues"]:
            issues.append({"path": change["path"], **issue})
    return issues


def print_report(report):
    summary = report["summary"]

    print("=== Repository Preflight ===")
    print(f"Current branch: {terminal_safe(report['branch'])}")
    print(f"Base: {terminal_safe(report['base'])}")
    print(f"Head: {terminal_safe(report['head'])}")
    print(f"Repository state: {terminal_safe(report['repository_state'])}")

    topology = report.get("topology")
    if topology is not None:
        print()
        print("Topology:")
        print(f"Base SHA: {terminal_safe(topology['base_sha'])}")
        print(f"Head SHA: {terminal_safe(topology['head_sha'])}")
        print(f"Merge base: {terminal_safe(topology['merge_base'])}")
        print(f"Behind: {terminal_safe(topology['behind'])}")
        print(f"Ahead: {terminal_safe(topology['ahead'])}")
        print(f"Relationship: {terminal_safe(topology['relationship'])}")
        print(f"FF eligible: {'YES' if topology['ff_eligible'] else 'NO'}")

    collisions = report.get("collisions")
    if collisions is not None:
        print()
        print("Collisions:")
        print(f"Count: {terminal_safe(collisions['count'])}")
        print(f"Binary-sensitive: {terminal_safe(collisions['binary_sensitive_count'])}")
        if not collisions["files"]:
            print("- None")
        else:
            for item in collisions["files"]:
                path = terminal_safe(item["path"])
                file_type = terminal_safe(item["file_type"])
                if item["binary_sensitive"]:
                    print(f"- {path} [{file_type}, BINARY-SENSITIVE]")
                else:
                    print(f"- {path} [{file_type}]")

    print()
    print(f"Technical risk: {terminal_safe(report['technical_risk'])}")
    print(f"Governance: {terminal_safe(report['governance_status'])}")
    print()
    print(f"Changed files: {summary['total_changes']}")
    print(f"High risk: {summary['high_count']}")
    print(f"Medium risk: {summary['medium_count']}")
    print(f"Low risk: {summary['low_count']}")
    print(f"Manual reviews: {summary['manual_review_count']}")

    if summary.get("status_counts"):
        mix = ", ".join(
            f"{terminal_safe(status)}={count}"
            for status, count in summary["status_counts"].items()
        )
        print(f"Git status mix: {mix}")

    if summary.get("file_type_counts"):
        mix = ", ".join(
            f"{terminal_safe(file_type)}={count}"
            for file_type, count in summary["file_type_counts"].items()
        )
        print(f"File types: {mix}")

    if summary.get("owner_counts"):
        mix = ", ".join(
            f"{terminal_safe(owner)}={count}"
            for owner, count in summary["owner_counts"].items()
        )
        print(f"Owners: {mix}")

    if report["repository_state"] == "DIRTY":
        print()
        print("Repository warning:")
        print("- Uncommitted changes detected. They are not included in the branch diff.")

    print()
    print("Required checks:")
    if not summary["required_checks"]:
        print("- None")
    else:
        for check in summary["required_checks"]:
            print(f"- {terminal_safe(check)}")

    print()
    print("Manual review:")
    if not summary["manual_review_files"]:
        print("- None")
    else:
        for path in summary["manual_review_files"]:
            print(f"- {terminal_safe(path)}")

    issues = collect_governance_issues(report)
    print()
    print("Governance issues:")
    if not issues:
        print("- None")
    else:
        for issue in issues:
            print(
                f"- [{terminal_safe(issue['code'])}] "
                f"{terminal_safe(issue['path'])}"
            )
            print(f"  {terminal_safe(issue['message'])}")


def print_json_report(report):
    print(json.dumps(report, indent=2, sort_keys=True))
