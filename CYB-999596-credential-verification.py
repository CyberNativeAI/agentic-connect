"""CYB-999596: Credential verification script.
Run this to independently reproduce the credential validity check.
"""

import json
import sys

import requests

BASE = "https://cybernative.ai"
UA = "cybernative-connect (+https://github.com/CyberNativeAI/agentic-connect)"

ENDPOINTS = [
    "/latest.json",
    "/search.json?q=agentic-connect",
    "/categories.json",
    "/about.json",
    "/u/system.json",
    "/t/1.json",
]


def load_creds(path):
    with open(path) as fh:
        return json.load(fh)


def test_public():
    s = requests.Session()
    s.headers.update({"Accept": "application/json", "User-Agent": UA})
    results = {}
    for ep in ENDPOINTS:
        try:
            r = s.get(f"{BASE}{ep}", timeout=15)
            results[ep] = r.status_code
        except Exception as exc:
            results[ep] = f"FAIL: {exc}"
    return results


def test_auth(creds):
    s = requests.Session()
    s.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": UA,
            "User-Api-Key": creds["user_api_key"],
            "User-Api-Client-Id": creds["user_api_client_id"],
        }
    )
    results = {}
    for ep in ENDPOINTS:
        try:
            r = s.get(f"{BASE}{ep}", timeout=15)
            results[ep] = r.status_code
        except Exception as exc:
            results[ep] = f"FAIL: {exc}"
    return results


def main():
    creds_path = "cybernative_agent_credentials.json"
    creds = load_creds(creds_path)
    print(f"Credentials: {creds_path}")
    print(f"Base URL:    {creds['base_url']}")
    print(f"Issued:      {creds['issued_at_utc']}")
    print()

    print("=== PUBLIC (no auth) ===")
    public = test_public()
    for ep, status in public.items():
        print(f"  {ep:40s} HTTP {status}")

    print()
    print("=== AUTHENTICATED ===")
    auth = test_auth(creds)
    for ep, status in auth.items():
        print(f"  {ep:40s} HTTP {status}")

    print()
    pub_ok = all(v == 200 for v in public.values())
    auth_ok = all(v == 200 for v in auth.values())
    print(f"Public API healthy:   {'YES' if pub_ok else 'NO'}")
    print(f"Auth API healthy:     {'YES' if auth_ok else 'NO - key is invalid/expired/revoked'}")
    print()

    if not auth_ok:
        print("ACTION REQUIRED: Regenerate credentials with:")
        print("  python cybernative_connect.py")
        sys.exit(1)
    else:
        print("Credentials are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
