"""
Community Engineer operator session — exercises realistic workflows and records gaps.
Read-only by default; set DRY_RUN=0 to allow a single test reply (not used in CYB-102).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cybernative_tools import (  # noqa: E402
    CyberNativeAPIError,
    CyberNativeClient,
    CyberNativeConfigurationError,
)

DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"


def attempt(name: str, fn):
    """Run fn(), return {name, ok, detail, data?}."""
    try:
        result = fn()
        return {"action": name, "ok": True, "detail": "success", "sample": _sample(result)}
    except CyberNativeConfigurationError as exc:
        return {"action": name, "ok": False, "detail": f"config: {exc}"}
    except CyberNativeAPIError as exc:
        return {"action": name, "ok": False, "detail": f"api: {exc}"}
    except AttributeError as exc:
        return {"action": name, "ok": False, "detail": f"missing_method: {exc}"}
    except Exception as exc:  # noqa: BLE001 — session probe
        return {"action": name, "ok": False, "detail": f"error: {type(exc).__name__}: {exc}"}


def _sample(obj, max_len: int = 400):
    if obj is None:
        return None
    if isinstance(obj, (list, dict)):
        text = json.dumps(obj, default=str)[:max_len]
        return text + ("..." if len(text) >= max_len else "")
    return str(obj)[:max_len]


def main() -> int:
    report: dict = {"dry_run": DRY_RUN, "attempts": [], "wishlist_notes": []}

    try:
        client = CyberNativeClient(credentials_file=str(ROOT / "cybernative_agent_credentials.json"))
    except CyberNativeConfigurationError as exc:
        print(json.dumps({"fatal": str(exc)}, indent=2))
        return 1

    # --- Workflows from CYB-102 acceptance ---
    report["attempts"].append(attempt("get_latest_topics", lambda: client.get_latest_topics(8)))

    latest = report["attempts"][-1]
    topic_id = None
    topic_url = None
    author_username = None
    if latest.get("ok"):
        topics = client.get_latest_topics(8)
        if topics:
            t0 = topics[0]
            topic_id = t0.get("id")
            topic_url = client.get_topic_url(t0)
            report["sample_topic"] = {
                "id": topic_id,
                "title": t0.get("title"),
                "url": topic_url,
                "posts_count": t0.get("posts_count"),
                "reply_count": t0.get("reply_count"),
                "last_posted_at": t0.get("last_posted_at"),
            }

    if topic_id:
        report["attempts"].append(
            attempt("read_topic_summarize", lambda: _summarize_topic(client, topic_id))
        )
        topic_data = client.read_topic(topic_id)
        posts = topic_data.get("post_stream", {}).get("posts", [])
        if posts:
            author_username = posts[0].get("username")

    report["attempts"].append(attempt("search_unanswered", lambda: client.search("status:unsolved")))
    report["attempts"].append(attempt("search_community_ai", lambda: client.search("agent OR community")))
    report["attempts"].append(attempt("get_categories", lambda: client.get_categories()))

    if author_username:
        report["attempts"].append(
            attempt("get_user_profile", lambda: client.get_user(author_username))
        )

    # Missing client methods — community operator expectations
    for missing in (
        "follow_user",
        "follow_topic",
        "bookmark_topic",
        "like_post",
        "react_to_post",
        "list_notifications",
        "send_private_message",
        "list_unread",
        "get_topic_participants",
        "list_bookmarks",
    ):
        report["attempts"].append(
            attempt(
                f"client.{missing}",
                lambda m=missing: getattr(client, m)(),  # type: ignore[attr-defined]
            )
        )

    # Draft reply (dry-run: validate we can read, not post)
    if topic_id and DRY_RUN:
        report["attempts"].append(
            {
                "action": "draft_reply_dry_run",
                "ok": True,
                "detail": "skipped POST; would call reply_to_topic",
                "sample": f"topic_id={topic_id}",
            }
        )
    elif topic_id:
        report["attempts"].append(
            attempt(
                "reply_to_topic_test",
                lambda: client.reply_to_topic(
                    topic_id,
                    "_CE operator session test — please ignore if unexpected._",
                ),
            )
        )

    report["wishlist_notes"] = _build_wishlist(report)
    print(json.dumps(report, indent=2, default=str))
    return 0


def _summarize_topic(client: CyberNativeClient, topic_id: int) -> dict:
    topic = client.read_topic(topic_id)
    posts = topic.get("post_stream", {}).get("posts", [])
    return {
        "title": topic.get("title"),
        "post_count": len(posts),
        "usernames": [p.get("username") for p in posts[:5]],
        "last_post_excerpt": (posts[-1].get("cooked", "")[:120] if posts else ""),
    }


def _build_wishlist(report: dict) -> list[dict]:
    """Prioritized gaps from attempted actions."""
    missing = [a for a in report["attempts"] if not a.get("ok")]
    priorities = []

    def add(priority: str, item: str, why: str, blocked_actions: list[str]):
        priorities.append(
            {"priority": priority, "item": item, "why": why, "blocked_actions": blocked_actions}
        )

    missing_names = {a["action"] for a in missing}

    if any("follow" in n for n in missing_names):
        add(
            "P0",
            "follow_user / follow_topic",
            "Cannot monitor recurring community threads or champions without follow APIs.",
            ["follow_user", "follow_topic"],
        )
    if any("bookmark" in n for n in missing_names):
        add(
            "P0",
            "bookmark_topic + list_bookmarks",
            "Operators need a triage queue; bookmarks are the minimal persistence layer.",
            ["bookmark_topic", "list_bookmarks"],
        )
    if any("like" in n or "react" in n for n in missing_names):
        add(
            "P1",
            "like_post / react_to_post",
            "Low-friction engagement signal before drafting full replies.",
            ["like_post", "react_to_post"],
        )
    if any("notification" in n or "unread" in n for n in missing_names):
        add(
            "P1",
            "list_notifications / list_unread",
            "Inbox-driven workflow: surface what changed since last session.",
            ["list_notifications", "list_unread"],
        )
    if any("private_message" in n or "send_private" in n for n in missing_names):
        add(
            "P2",
            "send_private_message",
            "Escalations and sensitive feedback often need DM, not public reply.",
            ["send_private_message"],
        )
    if any("participants" in n for n in missing_names):
        add(
            "P2",
            "get_topic_participants",
            "Identify who to @mention or follow after reading a thread.",
            ["get_topic_participants"],
        )

    # API-level gaps from successful reads
    for a in report["attempts"]:
        if a.get("action") == "search_unanswered" and not a.get("ok"):
            add(
                "P1",
                "search helpers or documented query syntax",
                "Operators need 'unanswered' triage; raw search failed or needs docs.",
                ["search_unanswered"],
            )

    return priorities


if __name__ == "__main__":
    raise SystemExit(main())
