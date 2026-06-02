"""Post Paperclip issue comment and update status."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: paperclip_update_issue.py <comment.md> <status>", file=sys.stderr)
        return 2

    comment_path, status = sys.argv[1], sys.argv[2]
    issue_id = os.environ["PAPERCLIP_TASK_ID"]
    api = os.environ["PAPERCLIP_API_URL"].rstrip("/")
    run_id = os.environ["PAPERCLIP_RUN_ID"]
    key = os.environ["PAPERCLIP_API_KEY"]

    comment = open(comment_path, encoding="utf-8").read()

    def call(method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
        url = f"{api}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "X-Paperclip-Run-Id": run_id,
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    code, body = call("POST", f"/api/issues/{issue_id}/comments", {"body": comment})
    print(f"comment HTTP {code}: {body[:500]}")
    if code >= 400:
        return 1

    code, body = call("PATCH", f"/api/issues/{issue_id}", {"status": status})
    print(f"patch HTTP {code}: {body[:500]}")
    return 0 if code < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
