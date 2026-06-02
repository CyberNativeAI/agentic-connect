"""CYB-98: probe Discourse endpoints for likes, reactions, chat, DMs, notifications, bookmarks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from cybernative_tools import CyberNativeClient, CyberNativeAPIError

RESULTS: list[dict] = []


def probe(name: str, method: str, path: str, **kwargs) -> dict:
    client = probe.client  # type: ignore[attr-defined]
    url = f"{client.base_url}{path}"
    try:
        r = requests.request(
            method,
            url,
            headers=kwargs.pop("headers", client.headers),
            timeout=client.timeout,
            **kwargs,
        )
        body_preview = ""
        try:
            data = r.json()
            body_preview = json.dumps(data)[:400]
        except ValueError:
            body_preview = (r.text or "")[:400]
        entry = {
            "name": name,
            "method": method,
            "path": path,
            "status": r.status_code,
            "ok": r.ok,
            "preview": body_preview,
        }
    except requests.exceptions.RequestException as exc:
        entry = {"name": name, "method": method, "path": path, "error": str(exc)}
    RESULTS.append(entry)
    return entry


def main() -> None:
    client = CyberNativeClient()
    probe.client = client  # type: ignore[attr-defined]

    topics = client.get_latest_topics(3)
    topic_id = topics[0]["id"] if topics else None
    topic = client.read_topic(topic_id) if topic_id else {}
    posts = topic.get("post_stream", {}).get("posts", []) if topic else []
    post_id = posts[0]["id"] if posts else None

    print(f"base_url={client.base_url}")
    print(f"sample_topic_id={topic_id} sample_post_id={post_id}")

    # Notifications (scope requested at connect time)
    probe("notifications", "GET", "/notifications.json")

    # Bookmarks list
    probe("bookmarks", "GET", "/bookmarks.json")

    # Site / chat enabled flags
    probe("site", "GET", "/site.json")

    # Chat plugin endpoints (Discourse Chat)
    probe("chat_channels", "GET", "/chat/api/channels.json")
    probe("chat_threads", "GET", "/chat/api/threads.json")

    # User chats (alternate paths)
    probe("chat_channels_v2", "GET", "/chat/channels.json")

    # Direct messages style
    probe("private_messages", "GET", "/private-messages.json")

    if post_id:
        # Standard Discourse like (post_action type 2)
        probe(
            "like_post",
            "POST",
            f"/post_actions.json",
            headers={**client.headers, "Content-Type": "application/json"},
            json={"id": post_id, "post_action_type_id": 2},
        )

        # Emoji reaction via discourse-reactions plugin (common)
        probe(
            "emoji_reaction",
            "PUT",
            f"/discourse-reactions/posts/{post_id}/custom-reactions/+1/toggle.json",
            headers={**client.headers, "Content-Type": "application/json"},
        )

        probe(
            "reactions_list",
            "GET",
            f"/discourse-reactions/posts/reactions.json?post_id={post_id}",
        )

    if topic_id and post_id:
        # Bookmark a post
        probe(
            "bookmark_post",
            "POST",
            "/bookmarks.json",
            headers={**client.headers, "Content-Type": "application/json"},
            json={"bookmarkable_id": post_id, "bookmarkable_type": "Post"},
        )

    # Search chat-specific
    try:
        client.search("in:chat")
    except CyberNativeAPIError as exc:
        RESULTS.append({"name": "search_in_chat", "error": str(exc)})

    print("\n=== PROBE SUMMARY ===")
    for r in RESULTS:
        status = r.get("status", r.get("error", "?"))
        print(f"{r['name']}: {r.get('method','')} {r.get('path','')} -> {status}")
        if r.get("preview"):
            print(f"  preview: {r['preview'][:200]}")

    out = Path(__file__).with_name("_ce_cyb98_probe_results.json")
    out.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
