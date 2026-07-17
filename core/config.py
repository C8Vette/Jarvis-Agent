from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    path = ROOT / relative_path
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(relative_path: str, data: dict) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def load_device_config() -> dict:
    return load_yaml("config/device.yaml")


def save_device_config(data: dict) -> None:
    save_yaml("config/device.yaml", data)


def load_permissions() -> dict:
    return load_yaml("config/permissions.yaml")


def save_permissions(data: dict) -> None:
    save_yaml("config/permissions.yaml", data)


def load_user_config() -> dict:
    return load_yaml("config/user.yaml")
