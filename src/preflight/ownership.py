from .errors import ConfigError


def rule_matches(path, rule):
    match_type = rule.get("match", "prefix")
    rule_path = rule["path"]

    if match_type == "path_exact":
        return path == rule_path
    if match_type == "prefix":
        return path.startswith(rule_path)

    raise ConfigError(f"Unsupported ownership match type: {match_type}")


def get_owner(path, rules, default_owner=None):
    matches = [rule for rule in rules if rule_matches(path, rule)]

    if not matches:
        return default_owner if default_owner is not None else "Unknown"

    def specificity(rule):
        match_rank = 1 if rule.get("match", "prefix") == "path_exact" else 0
        return (len(rule["path"]), match_rank)

    most_specific = max(matches, key=specificity)
    return most_specific["owner"]
