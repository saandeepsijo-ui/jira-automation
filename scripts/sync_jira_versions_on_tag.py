#!/usr/bin/env python3
"""On GitHub Release published: create Jira version and set Fix Version on Done bugs linked via PRs.

Triggered by workflow `release: published` (not raw tag pushes). TAG is the release's tag_name.

Env:
  TAG                 — release tag name (required), e.g. test-1.0.0
  JIRA_EMAIL          — service account / user email
  JIRA_API_TOKEN      — API token
  JIRA_CLOUD_ID       — Atlassian Cloud ID (preferred for scoped tokens)
  JIRA_BASE           — site URL fallback if no Cloud ID
  JIRA_PROJECT        — project key (default REL)
  GITHUB_TOKEN        — GitHub token with pull-requests:read
  GITHUB_REPOSITORY   — owner/repo (set automatically in Actions)
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def die(msg: str, code: int = 1) -> None:
    print(f"::error::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"ERROR: {msg}")
    sys.exit(code)


def jira_root() -> str:
    cloud_id = (os.environ.get("JIRA_CLOUD_ID") or "").strip()
    if cloud_id:
        return f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
    base = os.environ.get(
        "JIRA_BASE", "https://atimotors-team-c7ja40wb.atlassian.net"
    ).rstrip("/")
    return f"{base}/rest/api/3"


def jira_auth_header() -> str:
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        die("Set JIRA_EMAIL and JIRA_API_TOKEN")
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def http_json(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict | None = None,
) -> tuple[int, object | None]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw
        return e.code, payload


def jira(method: str, path: str, body: dict | None = None) -> tuple[int, object | None]:
    headers = {
        "Authorization": jira_auth_header(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    return http_json(method, jira_root() + path, headers, body)


def ensure_version(project: str, name: str) -> None:
    status, data = jira(
        "POST",
        "/version",
        {"name": name, "project": project, "released": True},
    )
    if status in (200, 201):
        print(f"Created Jira version {name!r} in {project}")
        return
    # Already exists / conflict
    msg = json.dumps(data) if data is not None else ""
    if status in (400, 409) and (
        "already exists" in msg.lower()
        or "a version with this name already exists" in msg.lower()
    ):
        print(f"Version {name!r} already exists — continuing")
        return
    # Some sites return 400 with different wording; check project versions list
    st2, versions = jira("GET", f"/project/{project}/versions")
    if st2 == 200 and isinstance(versions, list):
        if any(v.get("name") == name for v in versions):
            print(f"Version {name!r} already exists — continuing")
            return
    die(f"Failed to create version {name!r} ({status}): {data}")


def search_done_bugs_without_fix(project: str) -> list[str]:
    jql = (
        f"project = {project} AND issuetype = Bug "
        f"AND statusCategory = Done AND fixVersion is EMPTY"
    )
    keys: list[str] = []
    next_token = None
    while True:
        body: dict = {
            "jql": jql,
            "maxResults": 50,
            "fields": ["summary", "status", "fixVersions"],
        }
        if next_token:
            body["nextPageToken"] = next_token
        status, data = jira("POST", "/search/jql", body)
        if status != 200 or not isinstance(data, dict):
            # Fallback to older search endpoint
            q = urllib.parse.urlencode(
                {"jql": jql, "maxResults": 50, "fields": "summary"}
            )
            status, data = jira("GET", f"/search?{q}")
            if status != 200 or not isinstance(data, dict):
                die(f"JQL search failed ({status}): {data}")
            for issue in data.get("issues", []):
                keys.append(issue["key"])
            break
        for issue in data.get("issues", []):
            keys.append(issue["key"])
        next_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_token:
            break
    return keys


def github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        die("Set GITHUB_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def find_merged_pr_shas(issue_key: str) -> list[str]:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        die("Set GITHUB_REPOSITORY (owner/repo)")
    # Search merged PRs in this repo mentioning the key in the title
    query = f'repo:{repo} is:pr is:merged in:title "{issue_key}"'
    url = (
        "https://api.github.com/search/issues?"
        + urllib.parse.urlencode({"q": query, "per_page": 20})
    )
    status, data = http_json("GET", url, github_headers())
    if status != 200 or not isinstance(data, dict):
        print(f"  GitHub search failed for {issue_key}: {status} {data}")
        return []

    shas: list[str] = []
    for item in data.get("items", []):
        title = item.get("title") or ""
        if not re.search(rf"\b{re.escape(issue_key)}\b", title):
            continue
        pr_url = item.get("pull_request", {}).get("url")
        if not pr_url:
            continue
        st, pr = http_json("GET", pr_url, github_headers())
        if st != 200 or not isinstance(pr, dict):
            continue
        sha = pr.get("merge_commit_sha")
        if sha:
            shas.append(sha)
            print(f"  Found merged PR #{pr.get('number')} merge={sha[:12]}… title={title!r}")
    return shas


def tag_contains_commit(tag: str, sha: str) -> bool:
    try:
        out = subprocess.check_output(
            ["git", "tag", "--contains", sha],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False
    tags = {line.strip() for line in out.splitlines() if line.strip()}
    return tag in tags


def set_fix_version(issue_key: str, version_name: str) -> None:
    status, data = jira(
        "PUT",
        f"/issue/{issue_key}",
        {"update": {"fixVersions": [{"add": {"name": version_name}}]}},
    )
    if status not in (200, 204):
        die(f"Failed to set fixVersion on {issue_key} ({status}): {data}")
    print(f"  Set fixVersion={version_name!r} on {issue_key}")


def add_comment(issue_key: str, text: str) -> None:
    body = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        }
    }
    status, data = jira("POST", f"/issue/{issue_key}/comment", body)
    if status not in (200, 201):
        print(f"  Warning: comment on {issue_key} failed ({status}): {data}")
    else:
        print(f"  Commented on {issue_key}")


def main() -> int:
    tag = (os.environ.get("TAG") or "").strip()
    project = (os.environ.get("JIRA_PROJECT") or "REL").strip()
    if not tag:
        die("Set TAG to the git tag name")

    print(f"Tag={tag!r} project={project!r}")
    print(f"Jira API root={jira_root()}")

    ensure_version(project, tag)

    keys = search_done_bugs_without_fix(project)
    print(f"Candidate bugs without fixVersion: {keys or '(none)'}")

    for key in keys:
        print(f"Processing {key}…")
        shas = find_merged_pr_shas(key)
        if not shas:
            add_comment(
                key,
                f"Fix Version sync ({tag}): no merged PR in this GitHub repo "
                f"with {key} in the title. Fix Version was left empty.",
            )
            continue

        in_tag = [sha for sha in shas if tag_contains_commit(tag, sha)]
        if in_tag:
            set_fix_version(key, tag)
        else:
            short = ", ".join(s[:12] for s in shas)
            add_comment(
                key,
                f"Fix Version sync ({tag}): merged PR commit(s) [{short}] "
                f"were NOT found in tag {tag}. Fix Version was not set. "
                f"Verify cherry-pick or whether the fix was deferred.",
            )

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
