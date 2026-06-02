import time
from datetime import datetime, timezone
from cybernative_tools import CyberNativeClient

client = CyberNativeClient()
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
title = "[agentic-connect QA] CYB-162 workflow probe %s" % stamp
body = "Automated CommunityEngineer probe from CYB-162. Safe to delete."

created = client.create_topic(title, body, category_id=2)
topic_id = created.get("topic_id") or created.get("topic", {}).get("id")
post_id = created.get("id")
print("CREATE topic_id=%s post_id=%s" % (topic_id, post_id))

reply = client.reply_to_topic(topic_id, "Reply probe — please ignore.")
reply_post = reply.get("id")
print("REPLY post_id=%s" % reply_post)

liked = client.like_post(post_id)
print("LIKE ok")

client.unlike_post(post_id)
print("UNLIKE ok")

bm = client.bookmark_post(post_id)
print("BOOKMARK ok keys=%s" % list(bm.keys())[:4])

# cleanup bookmark via list (no delete helper in client)
print("DONE write-path smoke")
