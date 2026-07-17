from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import ROOT, load_device_config, save_device_config

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
HEADERS = ["From", "Subject", "Date"]


@dataclass
class GmailSettings:
    enabled: bool = False
    credentials_path: Path = ROOT / "data" / "google" / "credentials.json"
    token_path: Path = ROOT / "data" / "google" / "token.json"
    max_messages: int = 8
    query: str = "newer_than:7d -category:promotions"
    important_query: str = "is:unread newer_than:7d"

    @classmethod
    def from_config(cls) -> "GmailSettings":
        config = load_device_config().get("integrations", {}).get("gmail", {})
        return cls(
            enabled=bool(config.get("enabled", False)),
            credentials_path=_path(config.get("credentials_path", "data/google/credentials.json")),
            token_path=_path(config.get("token_path", "data/google/token.json")),
            max_messages=int(config.get("max_messages", 8)),
            query=str(config.get("query", "newer_than:7d -category:promotions")),
            important_query=str(config.get("important_query", "is:unread newer_than:7d")),
        )


def gmail_connect(_: str = "") -> str:
    settings = GmailSettings.from_config()
    try:
        service = _gmail_service(settings, interactive=True)
        profile = service.users().getProfile(userId="me").execute()
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        return f"Gmail connection failed: {exc}"

    _set_gmail_enabled(True)
    return f"Gmail connected for {profile.get('emailAddress', 'this account')}."


def gmail_status(_: str = "") -> str:
    settings = GmailSettings.from_config()
    if not _google_libs_available():
        return _missing_dependency_message()
    if not settings.credentials_path.exists():
        return f"Gmail is not configured. Missing OAuth credentials: {settings.credentials_path}"
    if not settings.token_path.exists():
        return "Gmail credentials are present, but the account is not connected yet."
    if not settings.enabled:
        return "Gmail is connected but disabled in config/device.yaml."

    try:
        service = _gmail_service(settings, interactive=False)
        profile = service.users().getProfile(userId="me").execute()
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        return f"Gmail status check failed: {exc}"

    return f"Gmail is enabled for {profile.get('emailAddress', 'this account')}."


def gmail_digest(target: str = "") -> str:
    result = gmail_digest_data(query=target.strip() or None)
    if not result.get("configured"):
        return result.get("message", "Gmail is not configured yet.")

    messages = result.get("messages", [])
    if not messages:
        return "No matching Gmail messages found."

    parts = []
    for message in messages[:5]:
        sender = message.get("from", "unknown sender")
        subject = message.get("subject", "no subject")
        parts.append(f"{sender}: {subject}")
    extra = len(messages) - len(parts)
    if extra > 0:
        parts.append(f"{extra} more")
    return "Gmail digest: " + "; ".join(parts) + "."


def gmail_digest_data(query: str | None = None, max_messages: int | None = None) -> dict[str, Any]:
    settings = GmailSettings.from_config()
    if not settings.enabled:
        return {"configured": False, "messages": [], "message": "Gmail is disabled."}
    if not _google_libs_available():
        return {"configured": False, "messages": [], "message": _missing_dependency_message()}
    if not settings.credentials_path.exists():
        return {
            "configured": False,
            "messages": [],
            "message": f"Missing Gmail OAuth credentials at {settings.credentials_path}.",
        }
    if not settings.token_path.exists():
        return {
            "configured": False,
            "messages": [],
            "message": "Gmail account is not connected yet.",
        }

    try:
        service = _gmail_service(settings, interactive=False)
        messages = _fetch_messages(
            service,
            query=query or settings.important_query,
            max_results=max_messages or settings.max_messages,
        )
    except RuntimeError as exc:
        return {"configured": False, "messages": [], "message": str(exc)}
    except Exception as exc:
        return {"configured": False, "messages": [], "message": f"Gmail read failed: {exc}"}

    return {"configured": True, "messages": messages, "message": ""}


def _fetch_messages(service, query: str, max_results: int) -> list[dict[str, Any]]:
    response = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=query)
        .execute()
    )
    summaries = []
    for item in response.get("messages", []):
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=HEADERS,
            )
            .execute()
        )
        headers = _headers(message)
        summaries.append(
            {
                "id": message.get("id", ""),
                "thread_id": message.get("threadId", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
            }
        )
    return summaries


def _gmail_service(settings: GmailSettings, interactive: bool):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(_missing_dependency_message()) from exc

    creds = None
    if settings.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(settings.token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif interactive:
            if not settings.credentials_path.exists():
                raise RuntimeError(f"Missing OAuth credentials: {settings.credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(settings.credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise RuntimeError("Gmail account needs authorization. Run: python main.py --gmail-connect")

        settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        settings.token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def _headers(message: dict[str, Any]) -> dict[str, str]:
    headers = {}
    for header in message.get("payload", {}).get("headers", []):
        name = str(header.get("name", "")).lower()
        value = str(header.get("value", ""))
        if name:
            headers[name] = value
    return headers


def _set_gmail_enabled(enabled: bool) -> None:
    config = load_device_config()
    integrations = config.setdefault("integrations", {})
    gmail = integrations.setdefault("gmail", {})
    gmail["enabled"] = enabled
    save_device_config(config)


def _path(value: object) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def _google_libs_available() -> bool:
    try:
        import google.auth.transport.requests  # noqa: F401
        import google.oauth2.credentials  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def _missing_dependency_message() -> str:
    return "Gmail integration needs dependencies. Run: pip install -r requirements-integrations.txt"
