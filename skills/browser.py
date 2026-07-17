import os
import webbrowser
from urllib.parse import quote_plus

from core.config import load_device_config

def open_website(name_or_url: str) -> str:
    config = load_device_config()
    websites = config.get("websites", {})

    url = websites.get(name_or_url.lower(), name_or_url)

    if not url.startswith("http"):
        url = "https://" + url

    if not webbrowser.open(url, new=2):
        os.startfile(url)

    return f"Opened {url}"


def search_web(query: str) -> str:
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    return open_website(url)


def search_youtube(query: str) -> str:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return open_website(url)
