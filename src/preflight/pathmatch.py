def canonical_prefix(prefix):
    """Normalize a prefix so equivalent spellings compare equal.

    Backslashes become slashes and trailing slashes are removed, while
    internal path-segment boundaries are preserved.
    """
    return prefix.replace("\\", "/").rstrip("/")


def path_prefix_matches(path, prefix):
    """Return True when prefix matches complete repository path segments."""
    normalized_path = path.replace("\\", "/")
    normalized_prefix = canonical_prefix(prefix)

    if not normalized_prefix:
        return True

    return (
        normalized_path == normalized_prefix
        or normalized_path.startswith(f"{normalized_prefix}/")
    )
