from pathlib import Path
from core.config import load_device_config

def search_files(query: str) -> str:
    config = load_device_config()
    allowed_folders = config.get("allowed_folders", [])

    matches = []

    for folder in allowed_folders:
        root = Path(folder)
        if not root.exists():
            continue

        for path in root.rglob("*"):
            try:
                if query.lower() in path.name.lower():
                    matches.append(str(path))
            except PermissionError:
                continue

            if len(matches) >= 20:
                break

    if not matches:
        return f"No files found for: {query}"

    return "Found:\n" + "\n".join(matches[:20])