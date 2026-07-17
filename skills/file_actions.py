import os
from pathlib import Path

# The filesystem sandbox now lives in core.safety (single source of truth).
from core.safety import get_allowed_roots, is_allowed_path


def find_matching_files(query: str, max_results: int = 20) -> list[Path]:
    matches = []

    for root in get_allowed_roots():
        if not root.exists():
            continue

        for path in root.rglob("*"):
            try:
                if query.lower() in path.name.lower():
                    matches.append(path)
            except PermissionError:
                continue

            if len(matches) >= max_results:
                return matches

    return matches


def open_folder(folder_name: str) -> str:
    common_folders = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
    }

    folder = common_folders.get(folder_name.lower(), Path(folder_name))

    if not folder.exists():
        return f"I could not find this folder: {folder}"

    os.startfile(folder)
    return f"Opened folder: {folder}"


def open_best_file_match(query: str) -> str:
    matches = find_matching_files(query)

    if not matches:
        return f"I could not find a file matching: {query}"

    # Prefer the newest modified file.
    best_match = max(matches, key=lambda p: p.stat().st_mtime)

    if not is_allowed_path(best_match):
        return f"I found a match, but it is outside my allowed folders: {best_match}"

    os.startfile(best_match)
    return f"Opened: {best_match}"
