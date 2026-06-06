#!/usr/bin/env python3
"""Read-only example: list the latest CyberNative.ai topics.

Prerequisites (one-time):
  1. From repo root: pip install -e .
  2. Authorize once: python cybernative_connect.py

Run:
  python examples/read_latest_topics.py
"""

from __future__ import annotations

from cybernative_tools import CyberNativeClient


def main() -> None:
    client = CyberNativeClient()
    topics = client.get_latest_topics(limit=5)
    print(f"Latest {len(topics)} topic(s) on CyberNative.ai:\n")
    for topic in topics:
        print(f"- {topic['title']}")
        print(f"  {client.get_topic_url(topic)}\n")


if __name__ == "__main__":
    main()
