#!/usr/bin/env python3
"""Fail unless the PR title contains at least one Jira key that exists on the site.

Usage:
  export JIRA_BASE='https://atimotors-team-c7ja40wb.atlassian.net'
  export JIRA_EMAIL='...'
  export JIRA_API_TOKEN='...'
  export PR_TITLE='MOM-13 EA-5: fix something'
  python3 scripts/check_jira_pr_title.py
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def extract_keys(title: str) -> list[str]:
    # Preserve order, unique
    seen: set[str] = set()
    keys: list[str] = []
    for match in JIRA_KEY_RE.finditer(title or ""):
        key = match.group(1)
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def issue_exists(base: str, auth_header: str, key: str) -> tuple[bool, str]:
    url = f"{base.rstrip('/')}/rest/api/3/issue/{key}?fields=summary"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": auth_header,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            data = json.loads(resp.read().decode())
            summary = (data.get("fields") or {}).get("summary") or ""
            return True, summary
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return False, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main() -> int:
    title = os.environ.get("PR_TITLE", "")
    base = os.environ.get(
        "JIRA_BASE", "https://atimotors-team-c7ja40wb.atlassian.net"
    ).rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")

    if not email or not token:
        print("::error::Set JIRA_EMAIL and JIRA_API_TOKEN secrets.")
        return 1

    keys = extract_keys(title)
    print(f"PR title: {title!r}")
    print(f"Extracted keys: {keys or '(none)'}")

    if not keys:
        print(
            "::error::No Jira issue key found in PR title. "
            "Include at least one key, e.g. 'MOM-13: fix widget'."
        )
        return 1

    auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    missing: list[str] = []
    for key in keys:
        ok, detail = issue_exists(base, auth, key)
        if ok:
            print(f"OK  {key} — {detail}")
        else:
            print(f"MISS {key} — {detail}")
            missing.append(key)

    if missing:
        print(
            "::error::These Jira keys do not exist (or are not visible): "
            + ", ".join(missing)
        )
        return 1

    print(f"All {len(keys)} Jira key(s) exist on {base}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
