def calculate_technical_risk(change):
    status = change["git_status"]
    file_type = change["file_type"]
    old_file_type = change.get("old_file_type")

    if status == "D" and file_type in ("source", "asset", "map", "build_config"):
        return "HIGH"

    if status in ("R", "C"):
        if old_file_type in ("source", "asset", "map", "build_config") or file_type in (
            "source", "asset", "map", "build_config"
        ):
            return "MEDIUM"
        return "LOW"

    if file_type in ("source", "asset", "map", "build_config"):
        return "MEDIUM"

    return "LOW"


def calculate_confidence(change):
    file_type = change["file_type"]
    old_file_type = change.get("old_file_type")

    if file_type in ("asset", "map") or old_file_type in ("asset", "map"):
        return "LOW"
    if file_type in ("source", "build_config"):
        return "HIGH"
    return "MEDIUM"


def calculate_required_checks(change):
    checks = []
    status = change["git_status"]
    file_type = change["file_type"]
    old_file_type = change.get("old_file_type")

    if file_type == "source" or old_file_type == "source":
        checks.append("build verification")

    if status == "D" and file_type == "asset":
        checks.append("reference verification")
    elif file_type == "asset" or old_file_type == "asset":
        checks.append("asset verification")

    if file_type == "map" or old_file_type == "map":
        checks.append("map integration verification")

    if file_type == "build_config" or old_file_type == "build_config":
        checks.append("build/config verification")

    return checks


def get_governance_issues(change):
    issues = []

    if change["owner"] == "Unknown":
        issues.append(
            {
                "code": "OWNERSHIP_GAP",
                "priority": "HIGH",
                "message": f"No ownership rule matches {change['path']}",
            }
        )

    if change["git_status"] == "R":
        old_owner = change.get("old_owner", "Unknown")
        new_owner = change["owner"]

        if (
            old_owner != "Unknown"
            and new_owner != "Unknown"
            and old_owner != new_owner
        ):
            issues.append(
                {
                    "code": "OWNERSHIP_BOUNDARY_CROSSING",
                    "priority": "HIGH",
                    "message": f"Ownership changed from {old_owner} to {new_owner}",
                }
            )

    return issues


def needs_manual_review(change, technical_risk, confidence, governance_issues):
    status = change["git_status"]
    file_type = change["file_type"]
    old_file_type = change.get("old_file_type")

    # Source, build configuration, and maps deserve explicit human inspection.
    if file_type in ("source", "build_config", "map"):
        return True
    if old_file_type in ("source", "build_config", "map"):
        return True

    # High-risk changes or governance problems always require review.
    if technical_risk == "HIGH":
        return True
    if governance_issues:
        return True

    # Binary uncertainty alone should not flood the manual-review list.
    # Newly added assets remain covered by asset verification; modified,
    # renamed, copied, or deleted assets deserve explicit inspection.
    if file_type == "asset" and status != "A":
        return True
    if old_file_type == "asset":
        return True

    return False


def analyze_change(change):
    technical_risk = calculate_technical_risk(change)
    confidence = calculate_confidence(change)
    required_checks = calculate_required_checks(change)
    governance_issues = get_governance_issues(change)

    return {
        **change,
        "technical_risk": technical_risk,
        "confidence": confidence,
        "required_checks": required_checks,
        "governance_issues": governance_issues,
        "manual_review_required": needs_manual_review(
            change, technical_risk, confidence, governance_issues
        ),
    }
