"""CYB-98 final: chat message reactions, unlike, DMs, mark notification read."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from cybernative_tools import CyberNativeClient

client = CyberNativeClient()
RESULTS = []


def hit(name, method, path, **kwargs):
    r = requests.request(
        method,
        f"{client.base_url}{path}",
        headers=kwargs.pop("headers", client.headers),
        timeout=client.timeout,
        **kwargs,
    )
    preview = ""
    try:
        preview = json.dumps(r.json())[:500]
    except ValueError:
        preview = (r.text or "")[:500]
    RESULTS.append({"name": name, "status": r.status_code, "path": path, "preview": preview})
    print(f"{name}: {r.status_code}")


# Chat message like/reaction (message_id from prior probe)
msg_id = 43271
hit("chat_message_like", "POST", "/chat/api/messages/43271/reactions/heart.json")
hit("chat_message_react", "PUT", f"/chat/api/messages/{msg_id}/reactions/heart/toggle.json")
hit("chat_message_actions", "GET", f"/chat/api/messages/{msg_id}.json")

# DM paths
hit("user_messages", "GET", "/u/system/messages.json")
hit("private_messages_inbox", "GET", "/topics/private-messages.json")

# Notification mark read
notifs = client._request("GET", "/notifications.json")
nid = notifs.get("notifications", [{}])[0].get("id") if notifs.get("notifications") else None
if nid:
    hit(
        "mark_notification_read",
        "PUT",
        f"/notifications/mark-read.json",
        headers={**client.headers, "Content-Type": "application/json"},
        json={"id": nid},
    )

# List who liked post
hit("post_action_users", "GET", "/post_action_users.json?id=114801&post_action_type_id=2")

Path(__file__).with_name("_ce_cyb98_final_probe_results.json").write_text(
    json.dumps(RESULTS, indent=2), encoding="utf-8"
)
