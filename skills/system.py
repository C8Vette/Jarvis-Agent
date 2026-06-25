import shutil
import subprocess
from pathlib import Path
from core.config import load_device_config


def open_app(app_name: str) -> str:
    config = load_device_config()
    apps = config.get("apps", {})

    app_command = apps.get(app_name.lower())

    if not app_command:
        return f"I do not know how to open {app_name}. Add it to config/device.yaml."

    # If it is a direct exe path, check that it exists
    if app_command.lower().endswith(".exe"):
        path = Path(app_command)

        if not path.exists():
            return f"I found an app entry for {app_name}, but this path does not exist: {app_command}"

        subprocess.Popen([str(path)])
        return f"Opened {app_name}"

    # If it is a command like "code", check if Windows can find it
    command_name = app_command.split()[0]

    if shutil.which(command_name) is None and not Path(command_name).exists():
        return f"I tried to open {app_name}, but Windows could not find this command: {app_command}"

    subprocess.Popen(app_command, shell=True)
    return f"Opened {app_name}"