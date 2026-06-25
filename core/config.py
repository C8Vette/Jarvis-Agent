from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(relative_path: str) -> dict:
    path = ROOT / relative_path
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_device_config() -> dict:
    return load_yaml("config/device.yaml")

def load_permissions() -> dict:
    return load_yaml("config/permissions.yaml")