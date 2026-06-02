from cybernative_tools import CyberNativeClient
client = CyberNativeClient()
post_id = 114807
try:
    bm = client.bookmark_post(post_id)
    print("BOOKMARK pass", list(bm.keys())[:5])
except Exception as e:
    print("BOOKMARK fail", e)
try:
    client.unlike_post(post_id)
    print("UNLIKE unexpected pass")
except Exception as e:
    print("UNLIKE expected-ish", type(e).__name__)
