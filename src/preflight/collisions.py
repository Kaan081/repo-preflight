from .classifier import classify_file


BINARY_SENSITIVE_FILE_TYPES = frozenset({"asset", "map"})


def is_binary_sensitive(file_type):
    return file_type in BINARY_SENSITIVE_FILE_TYPES


def build_collision_report(paths, file_types):
    files = []
    for path in sorted(paths):
        file_type = classify_file(path, file_types)
        files.append(
            {
                "path": path,
                "file_type": file_type,
                "binary_sensitive": is_binary_sensitive(file_type),
            }
        )
    return {
        "count": len(files),
        "binary_sensitive_count": sum(1 for item in files if item["binary_sensitive"]),
        "files": files,
    }
