import subprocess
from core.config import load_device_config

def open_website(name_or_url: str) -> str:
    config = load_device_config()
    websites = config.get("websites", {})

    url = websites.get(name_or_url.lower(), name_or_url)

    if not url.startswith("http"):
        url = "https://" + url

    chrome = config.get("apps", {}).get("chrome")

    if chrome:
        subprocess.Popen([chrome, url])
    else:
        subprocess.Popen(["cmd", "/c", "start", url], shell=True)

    return f"Opened {url}"