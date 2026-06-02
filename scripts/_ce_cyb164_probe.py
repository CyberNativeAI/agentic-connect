"""CYB-164 exploration probe — sanitized JSON output, no secrets."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cybernative_tools import CyberNativeAPIError, CyberNativeClient

client = CyberNativeClient()
out: dict = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sections": {},
}

queries = [
    '"agentic-connect"',
    "status:unsolved agent",
    "in:title agentic",
    "category:site-feedback",
    "@system",
]
search_results = []
for q in queries:
    try:
        topics = client.search_topics(q, limit=2)
        search_results.append(
            {
                "query": q,
                "status": "ok",
                "topic_count": len(topics),
                "sample_titles": [str(t.get("title", ""))[:60] for t in topics[:2]],
            }
        )
    except Exception as exc:
        search_results.append(
            {"query": q, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
        )
out["sections"]["search_cookbook"] = search_results

try:
    user_payload = client.get_user("system")
    user = user_payload.get("user", {})
    out["sections"]["get_user"] = {
        "status": "ok",
        "username": user.get("username"),
        "has_user_object": "user" in user_payload,
    }
except Exception as exc:
    out["sections"]["get_user"] = {"status": "error", "error": str(exc)}

stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
title = f"[QA CYB-164] agentic-connect exploration probe {stamp}"
body = (
    "Automated CommunityEngineer probe for CYB-164. Safe to delete. "
    "Category id 2 (Site Feedback) only."
)
qa: dict = {"performed": False}
try:
    created = client.create_topic(title, body, category_id=2)
    topic = created.get("topic") or created
    tid = topic.get("id") or created.get("topic_id")
    url = client.get_topic_url(topic) if tid else None
    qa = {"performed": True, "topic_id": tid, "url": url, "title": title}
    if tid:
        readback = client.read_topic(tid)
        posts = readback.get("post_stream", {}).get("posts", [])
        qa["readback_post_count"] = len(posts)
        post_id = posts[0].get("id") if posts else None
        if post_id:
            try:
                client.like_post(post_id)
                qa["like"] = "ok"
            except CyberNativeAPIError as exc:
                qa["like"] = f"error: {exc}"
            try:
                client.unlike_post(post_id)
                qa["unlike"] = "ok"
            except CyberNativeAPIError as exc:
                qa["unlike"] = f"error: {exc}"
except Exception as exc:
    qa = {"performed": False, "error": f"{type(exc).__name__}: {exc}"}
out["sections"]["site_feedback_write"] = qa

try:
    bms = client.list_bookmarks()
    out["sections"]["list_bookmarks"] = {"status": "ok", "keys": list(bms.keys())[:5]}
except Exception as exc:
    out["sections"]["list_bookmarks"] = {"status": "error", "error": str(exc)}

result_path = Path(__file__).with_name("_ce_cyb164_probe_results.json")
result_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
