from .errors import ConfigError
from .pathmatch import canonical_prefix, path_prefix_matches


def rule_matches(path, rule):
    match_type = rule.get("match", "prefix")
    rule_path = rule["path"]

    if match_type == "path_exact":
        return path == rule_path
    if match_type == "prefix":
        return path_prefix_matches(path, rule_path)

    raise ConfigError(f"Unsupported ownership match type: {match_type}")


def get_owner(path, rules, default_owner=None):
    matches = [rule for rule in rules if rule_matches(path, rule)]

    if not matches:
        return default_owner if default_owner is not None else "Unknown"

    def specificity(rule):
        match_type = rule.get("match", "prefix")
        match_rank = 1 if match_type == "path_exact" else 0
        path = rule["path"]
        if match_type == "prefix":
            path_length = len(canonical_prefix(path))
        else:
            path_length = len(path)
        return (path_length, match_rank)

    most_specific = max(matches, key=specificity)
    return most_specific["owner"]
