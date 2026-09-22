def path_prefix_matches(path, prefix):
    """Return True when prefix matches complete repository path segments."""
    normalized_path = path.replace("\\", "/")
    normalized_prefix = prefix.replace("\\", "/").rstrip("/")

    if not normalized_prefix:
        return True

    return (
        normalized_path == normalized_prefix
        or normalized_path.startswith(f"{normalized_prefix}/")
    )
