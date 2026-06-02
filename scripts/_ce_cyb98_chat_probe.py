"""CYB-98 follow-up: chat messages and reaction discovery on cybernative.ai."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from cybernative_tools import CyberNativeClient

RESULTS: list[dict] = []


def req(client: CyberNativeClient, name: str, method: str, path: str, **kwargs) -> dict:
    url = f"{client.base_url}{path}"
    r = requests.request(
        method,
        url,
        headers=kwargs.pop("headers", client.headers),
        timeout=client.timeout,
        **kwargs,
    )
    preview = ""
    try:
        preview = json.dumps(r.json())[:600]
    except ValueError:
        preview = (r.text or "")[:600]
    entry = {"name": name, "method": method, "path": path, "status": r.status_code, "preview": preview}
    RESULTS.append(entry)
    print(f"{name}: {r.status_code}")
    return entry


def main() -> None:
    client = CyberNativeClient()

    site = client._request("GET", "/site.json")
    plugins = site.get("discourse_plugins", []) or []
    RESULTS.append({"name": "plugins", "plugins": plugins[:30], "count": len(plugins)})

    # Chat channel from prior probe
    channels = client._request("GET", "/chat/api/channels.json")
    ch_list = channels.get("channels", [])
    channel_id = ch_list[0]["id"] if ch_list else None
    RESULTS.append({"name": "first_channel", "id": channel_id, "title": ch_list[0].get("title") if ch_list else None})

    if channel_id:
        req(client, "channel_messages", "GET", f"/chat/api/channels/{channel_id}/messages.json")
        # Post a low-impact test message (agent QA)
        req(
            client,
            "post_chat_message",
            "POST",
            f"/chat/{channel_id}.json",
            headers={**client.headers, "Content-Type": "application/json"},
            json={"message": "[agentic-connect CYB-98 QA] probing chat send — please ignore"},
        )
        req(
            client,
            "post_chat_message_v2",
            "POST",
            "/chat/api/messages.json",
            headers={**client.headers, "Content-Type": "application/json"},
            json={"channel_id": channel_id, "message": "[CYB-98 QA v2] ignore"},
        )

    # Check post for existing actions / reaction data
    topic = client.read_topic(39263)
    post = topic["post_stream"]["posts"][0]
    post_id = post["id"]
    RESULTS.append(
        {
            "name": "post_fields",
            "keys": sorted(post.keys()),
            "actions_summary": post.get("actions_summary"),
            "reactions": post.get("reactions"),
        }
    )

    # Alternate reaction plugins
    for path in [
        f"/posts/{post_id}/reactions.json",
        f"/reactions/posts/{post_id}.json",
        f"/post_action_types.json",
    ]:
        req(client, f"alt_{path}", "GET", path)

    # Unlike cleanup from prior like probe
    req(
        client,
        "unlike_post",
        "POST",
        "/post_actions.json",
        headers={**client.headers, "Content-Type": "application/json"},
        json={"id": post_id, "post_action_type_id": 2, "flag_topic": False},
    )

    out = Path(__file__).with_name("_ce_cyb98_chat_probe_results.json")
    out.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
