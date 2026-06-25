from core.llm_router import llm_route
from skills.browser import open_website
from skills.system import open_app
from skills.files import search_files
from skills.file_actions import open_folder, open_best_file_match


def fallback_route(command: str) -> str:
    text = command.strip().lower()

    if text in ["open email", "open my email", "open gmail", "open up my email"]:
        return open_website("gmail")

    if text.startswith("find "):
        query = command.replace("find ", "", 1).strip()
        return search_files(query)

    return "I do not know how to do that yet."


def route_command(command: str) -> str:
    decision = llm_route(command)

    action = decision.get("action", "unknown")
    target = decision.get("target", "")
    reason = decision.get("reason", "")

    if text.startswith("open my downloads") or text.startswith("open downloads"):
        return open_folder("downloads")

    if text.startswith("open my documents") or text.startswith("open documents"):
        return open_folder("documents")

    if text.startswith("open my desktop") or text.startswith("open desktop"):
        return open_folder("desktop")

    if text.startswith("open my "):
        query = text.replace("open my ", "", 1).strip()
        return open_best_file_match(query)

    if text.startswith("open the newest "):
        query = text.replace("open the newest ", "", 1).strip()
        return open_best_file_match(query)

    if action == "open_website":
        return open_website(target)

    if action == "open_app":
        return open_app(target)

    if action == "search_files":
        return search_files(target)

    fallback_result = fallback_route(command)

    if fallback_result != "I do not know how to do that yet.":
        return fallback_result

    return f"I am not sure how to handle that yet. Reason: {reason}"