import sys
from cybernative_tools import CyberNativeClient

results = []

def record(name, fn):
    try:
        out = fn()
        if isinstance(out, list):
            summary = "count=%d" % len(out)
        elif isinstance(out, dict):
            keys = list(out.keys())[:6]
            summary = "keys=%s" % keys
        else:
            summary = type(out).__name__
        results.append((name, "PASS", summary))
    except Exception as e:
        results.append((name, "FAIL", "%s: %s" % (type(e).__name__, e)))

client = CyberNativeClient()
record("get_latest_topics", lambda: client.get_latest_topics(limit=3))
topics = client.get_latest_topics(limit=1)
tid = topics[0]["id"] if topics else None
if tid:
    record("read_topic", lambda: client.read_topic(tid))
record("get_categories", lambda: client.get_categories())
record("search", lambda: client.search("agentic-connect"))
record("search_topics", lambda: client.search_topics("agentic-connect", limit=3))
record("list_notifications", lambda: client.list_notifications())
record("list_bookmarks", lambda: client.list_bookmarks())
if hasattr(client, "get_session_info"):
    try:
        si = client.get_session_info()
        u = si.get("current_user", {}).get("username", "?")
        results.append(("get_session_info", "PASS", "username=%s" % u))
    except Exception as e:
        results.append(("get_session_info", "FAIL", str(e)))
else:
    results.append(("get_session_info", "BLOCKED", "method missing"))

for name, status, detail in results:
    print("%-7s %-22s %s" % (status, name, detail))
failed = [r for r in results if r[1] == "FAIL"]
sys.exit(1 if failed else 0)
