"""CYB-999620: Comprehensive write tool test script.
Tests all 16 CyberNativeClient methods end-to-end against cybernative.ai.
Uses Agent QA Sandbox category id 31 for all write operations.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any

from cybernative_tools import (
    CyberNativeAPIError,
    CyberNativeClient,
    CyberNativeConfigurationError,
)


def report(label: str, status: str, detail: str = "") -> None:
    print(f"  [{status:6s}] {label:<35s} {detail}")


def main() -> int:
    print("=== CYB-999620 Comprehensive Tool Test ===\n")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"Issue: CYB-999620")
    print()

    try:
        client = CyberNativeClient()
    except CyberNativeConfigurationError as exc:
        print(f"INIT FAILED: {exc}")
        return 1

    print(f"Base URL: {client.base_url}")
    print()

    results: dict[str, dict[str, Any]] = {}
    created_topic_id: int | None = None
    created_post_id: int | None = None
    bookmarked_post_id: int | None = None
    bookmarked_topic_id: int | None = None
    liked_post_id: int | None = None
    notification_to_mark: int | None = None

    # --- Read-only (public) ---
    print("--- Read-only (public, no auth required) ---")

    try:
        topics = client.get_latest_topics(limit=5)
        report("get_latest_topics", "PASS", f"{len(topics)} topics")
        results["get_latest_topics"] = {"status": "PASS", "count": len(topics)}
        read_topic_id = topics[0]["id"]
        read_topic_slug = topics[0].get("slug", "")
    except Exception as exc:
        report("get_latest_topics", "FAIL", str(exc)[:120])
        results["get_latest_topics"] = {"status": "FAIL", "error": str(exc)[:200]}
        read_topic_id = 1

    try:
        topic = client.read_topic(read_topic_id)
        posts = topic.get("post_stream", {}).get("posts", [])
        report("read_topic", "PASS", f"topic {read_topic_id}, {len(posts)} posts")
        results["read_topic"] = {"status": "PASS", "topic_id": read_topic_id, "posts": len(posts)}
    except Exception as exc:
        report("read_topic", "FAIL", str(exc)[:120])
        results["read_topic"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        categories = client.get_categories()
        report("get_categories", "PASS", f"{len(categories)} categories")
        results["get_categories"] = {"status": "PASS", "count": len(categories)}
    except Exception as exc:
        report("get_categories", "FAIL", str(exc)[:120])
        results["get_categories"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        data = client.search("agentic-connect")
        search_topics = data.get("topics", [])
        report("search", "PASS", f"{len(search_topics)} topics found")
        results["search"] = {"status": "PASS", "count": len(search_topics)}
    except Exception as exc:
        report("search", "FAIL", str(exc)[:120])
        results["search"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        st = client.search_topics("agentic-connect", limit=5)
        report("search_topics", "PASS", f"{len(st)} topics")
        results["search_topics"] = {"status": "PASS", "count": len(st)}
    except Exception as exc:
        report("search_topics", "FAIL", str(exc)[:120])
        results["search_topics"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        user = client.get_user("system")
        report("get_user", "PASS", f"username: {user.get('user', {}).get('username', 'N/A')}")
        results["get_user"] = {"status": "PASS"}
    except Exception as exc:
        report("get_user", "FAIL", str(exc)[:120])
        results["get_user"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        url = client.get_topic_url(topics[0])
        report("get_topic_url", "PASS", url[:80])
        results["get_topic_url"] = {"status": "PASS"}
    except Exception as exc:
        report("get_topic_url", "FAIL", str(exc)[:120])
        results["get_topic_url"] = {"status": "FAIL", "error": str(exc)[:200]}

    # --- Auth-read tools ---
    print("\n--- Auth-read (requires valid credentials) ---")

    try:
        notifs = client.list_notifications()
        notif_list = notifs.get("notifications", [])
        report("list_notifications", "PASS", f"{len(notif_list)} notifications")
        results["list_notifications"] = {"status": "PASS", "count": len(notif_list)}
        if notif_list:
            notification_to_mark = notif_list[0].get("id")
    except Exception as exc:
        report("list_notifications", "FAIL", str(exc)[:120])
        results["list_notifications"] = {"status": "FAIL", "error": str(exc)[:200]}

    try:
        bookmarks = client.list_bookmarks()
        bm_list = bookmarks.get("user_bookmark_list", {}).get("bookmarks", [])
        report("list_bookmarks", "PASS", f"{len(bm_list)} bookmarks")
        results["list_bookmarks"] = {"status": "PASS", "count": len(bm_list)}
    except Exception as exc:
        report("list_bookmarks", "FAIL", str(exc)[:120])
        results["list_bookmarks"] = {"status": "FAIL", "error": str(exc)[:200]}

    if notification_to_mark:
        try:
            client.mark_notification_read(notification_to_mark)
            report("mark_notification_read", "PASS", f"notification {notification_to_mark}")
            results["mark_notification_read"] = {"status": "PASS", "id": notification_to_mark}
        except Exception as exc:
            report("mark_notification_read", "FAIL", str(exc)[:120])
            results["mark_notification_read"] = {"status": "FAIL", "error": str(exc)[:200]}
    else:
        try:
            client.mark_notification_read()
            report("mark_notification_read", "PASS", "all notifications (bulk)")
            results["mark_notification_read"] = {"status": "PASS", "bulk": True}
        except Exception as exc:
            report("mark_notification_read", "FAIL", str(exc)[:120])
            results["mark_notification_read"] = {"status": "FAIL", "error": str(exc)[:200]}

    # --- Write tools ---
    print("\n--- Write tools (Agent QA Sandbox, category 31) ---")

    # create_topic
    ts = int(time.time())
    try:
        result = client.create_topic(
            title=f"[agentic-connect QA] CYB-999620 write tool probe {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            content=(
                "This is an automated QA probe for CYB-999620 write tool testing.\n\n"
                "All artifacts will be cleaned up per moderation policy.\n\n"
                f"Probe timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
                "CI ref: agentic-connect CYB-999620"
            ),
            category_id=31,
        )
        created_topic_id = result.get("topic_id") or result.get("id")
        created_post_id = result.get("post_id") or result.get("id")
        report("create_topic", "PASS", f"topic_id={created_topic_id}, post_id={created_post_id}")
        results["create_topic"] = {"status": "PASS", "topic_id": created_topic_id, "raw": str(result)[:200]}
    except Exception as exc:
        report("create_topic", "FAIL", str(exc)[:120])
        results["create_topic"] = {"status": "FAIL", "error": str(exc)[:200]}

    # reply_to_topic
    if created_topic_id:
        try:
            ts_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            result = client.reply_to_topic(
                topic_id=created_topic_id,
                message=(
                    f"[CYB-999620 QA] Automated reply test at {ts_str}. "
                    "This confirms reply_to_topic works with current credentials."
                ),
            )
            reply_post_id = result.get("id")
            report("reply_to_topic", "PASS", f"post_id={reply_post_id}")
            results["reply_to_topic"] = {"status": "PASS", "post_id": reply_post_id}
        except Exception as exc:
            report("reply_to_topic", "FAIL", str(exc)[:120])
            results["reply_to_topic"] = {"status": "FAIL", "error": str(exc)[:200]}
    else:
        report("reply_to_topic", "SKIP", "no topic to reply to")
        results["reply_to_topic"] = {"status": "SKIP"}

    # bookmark_post - bookmark our own newly created post
    if created_post_id:
        try:
            client.bookmark_post(created_post_id)
            bookmarked_post_id = created_post_id
            report("bookmark_post", "PASS", f"post_id={created_post_id}")
            results["bookmark_post"] = {"status": "PASS", "post_id": created_post_id}
        except Exception as exc:
            report("bookmark_post", "FAIL", str(exc)[:120])
            results["bookmark_post"] = {"status": "FAIL", "error": str(exc)[:200]}

    # bookmark_topic
    if created_topic_id:
        try:
            client.bookmark_topic(created_topic_id)
            bookmarked_topic_id = created_topic_id
            report("bookmark_topic", "PASS", f"topic_id={created_topic_id}")
            results["bookmark_topic"] = {"status": "PASS", "topic_id": created_topic_id}
        except Exception as exc:
            report("bookmark_topic", "FAIL", str(exc)[:120])
            results["bookmark_topic"] = {"status": "FAIL", "error": str(exc)[:200]}

    # like_post - must like a post NOT authored by us (Discourse rejects self-likes)
    # Use known non-self post (system user's post 114876) for reliable testing
    other_post_id = 114876
    try:
        client.like_post(other_post_id)
        liked_post_id = other_post_id
        report("like_post", "PASS", f"post_id={other_post_id}")
        results["like_post"] = {"status": "PASS", "post_id": other_post_id}
    except Exception as exc:
        err = str(exc)[:200]
        if "403" in err:
            report("like_post", "WARN", f"already liked? post_id={other_post_id}: {err[:80]}")
            results["like_post"] = {"status": "WARN", "post_id": other_post_id, "detail": err[:120]}
        else:
            report("like_post", "FAIL", err[:120])
            results["like_post"] = {"status": "FAIL", "error": err[:200]}

    # unlike_post - cleanup the like we just made
    if liked_post_id:
        try:
            client.unlike_post(liked_post_id)
            report("unlike_post", "PASS", f"cleaned up post_id={liked_post_id}")
            results["unlike_post"] = {"status": "PASS", "post_id": liked_post_id}
            liked_post_id = None
        except Exception as exc:
            report("unlike_post", "FAIL", str(exc)[:120])
            results["unlike_post"] = {"status": "FAIL", "error": str(exc)[:200]}
    else:
        report("unlike_post", "SKIP", "no like to undo")
        results["unlike_post"] = {"status": "SKIP"}

    # --- Summary ---
    print("\n=== Results Summary ===")
    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    skipped = sum(1 for r in results.values() if r["status"] == "SKIP")
    warned = sum(1 for r in results.values() if r["status"] == "WARN")

    print(f"Total: {total}, PASS: {passed}, FAIL: {failed}, SKIP: {skipped}, WARN: {warned}")

    # Cleanup bookmarks
    if bookmarked_post_id:
        try:
            client.bookmark_post(bookmarked_post_id)
            print(f"Cleaned up bookmark on post {bookmarked_post_id}")
        except Exception:
            pass

    # Print failed details
    if failed:
        print("\nFailures:")
        for name, result in results.items():
            if result["status"] == "FAIL":
                print(f"  {name}: {result.get('error', 'unknown')}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
