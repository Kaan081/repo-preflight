from .classifier import classify_file
from .ownership import get_owner


def build_change_context(raw_change, config):
    path = raw_change["path"]
    default_owner = config.get("default_owner")

    context = {
        **raw_change,
        "file_type": classify_file(path, config["file_types"]),
        "owner": get_owner(path, config["ownership"], default_owner),
    }

    if raw_change["git_status"] in ("R", "C"):
        old_path = raw_change["old_path"]
        context["old_owner"] = get_owner(
            old_path, config["ownership"], default_owner
        )
        context["old_file_type"] = classify_file(
            old_path, config["file_types"]
        )

    return context
