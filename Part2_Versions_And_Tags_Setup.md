# Part 2 (remaining): Affects Version + tag → Fix Version

**Site:** `https://atimotors-team-c7ja40wb.atlassian.net`  
**Project:** `REL` (Release Tracking) — **company-managed**  
**Repo:** [saandeepsijo-ui/jira-automation](https://github.com/saandeepsijo-ui/jira-automation)

This covers the rest of Part 2 after the [PR title Jira key gate](Part2_PR_Jira_Key_Gate_Setup.md).

---

## 1. Why a new project (`REL`)?

Team-managed `EA` does not handle Releases/Versions reliably via REST.  
`REL` is a **company-managed** software project created for version automation on the test site.

| Item | Value |
|---|---|
| Key | `REL` |
| Name | Release Tracking |
| Style | classic (company-managed) |
| Bootstrap Affects Version | `val-26.7` (unreleased) |
| Service account | `automation` (Administrators role) |

---

## 2. Concepts

| Field | Meaning | When set |
|---|---|---|
| **Affects Version** | Broken / found while testing this cycle | Bug **create** → `val-26.7` |
| **Fix Version** | Shipped in this **GitHub Release** | Release **published** → tag name |

```
Bug filed (Affects = val-26.7)
  → PR titled "REL-12: fix …" merges
  → GitHub Release published (tag e.g. test-1.0.0)
  → Jira version test-1.0.0 created
  → Done bugs whose merge commit is in that tag get Fix Version = test-1.0.0
```

**Important:** A plain `git push --tags` does **not** sync to Jira. Only publishing a **GitHub Release** (UI or `gh release create`) triggers the workflow.

---

## 3. Affects Version setup

### 3.1 Bootstrap (done on test site)

Version **`val-26.7`** exists on `REL`, unreleased, start date set.

To create another cycle later (UI):

1. **REL** → **Releases** (or Project settings → Versions)  
2. Create version, leave **unreleased**

### 3.2 Automation rule (configure in Jira UI)

Jira Automation rules are not created by this repo’s scripts. Add once under **REL → Project settings → Automation**:

| Setting | Value |
|---|---|
| Name | `Default Affects Version on Bug` |
| Trigger | Work item created |
| Condition | Issue type equals **Bug** |
| Action | Edit work item → **Affects versions** → choose **val-26.7** (or “copy from” latest unreleased if available) |

Until the rule exists, reporters (or API) can set Affects Version manually — e.g. `"versions": [{"name": "val-26.7"}]` on create.

---

## 4. GitHub Release → Fix Version (Actions)

### Files

| Path | Role |
|---|---|
| [`.github/workflows/sync-jira-versions-on-tag.yml`](.github/workflows/sync-jira-versions-on-tag.yml) | Runs on **`release: published`** only |
| [`scripts/sync_jira_versions_on_tag.py`](scripts/sync_jira_versions_on_tag.py) | Create version + set Fix Versions |

### Trigger

| Event | Syncs to Jira? |
|---|---|
| GitHub **Release** published | **Yes** — uses `release.tag_name` as the version name |
| Git tag push only | **No** |
| Draft release | **No** (until published) |
| Pre-release published | **Yes** (also fires `published`) |

### Behaviour

1. Create Jira version named as the release’s tag in project `REL` (`released: true`), skip if it already exists  
2. Find bugs: `project = REL AND issuetype = Bug AND statusCategory = Done AND fixVersion is EMPTY`  
3. For each key, find **merged PRs in this repo** whose **title** contains that key  
4. If merge commit is in that tag (`git tag --contains`) → add Fix Version  
5. Else comment on the issue (missing from tag, or no PR found)

### Secrets / variables (already used by PR gate)

| Name | Type | Purpose |
|---|---|---|
| `JIRA_EMAIL` | secret | Service account email |
| `JIRA_API_TOKEN` | secret | Token |
| `JIRA_CLOUD_ID` | variable | `994ccf9c-4f0e-43b4-9172-438a4bd06cc8` |
| `JIRA_BASE` | variable | Test site URL (fallback) |
| `JIRA_PROJECT` | variable | `REL` (default in workflow if unset) |

`GITHUB_TOKEN` is provided by Actions for PR search.

---

## 5. Smoke test

1. Create a Bug in `REL` with Affects Version `val-26.7`  
2. Transition it to **Done**  
3. Open a PR titled `REL-N: …`, merge to `main`  
4. Publish a GitHub Release for a new tag, e.g.  
   `gh release create test-1.0.1 --generate-notes --title "test-1.0.1"`  
   (or create the release in the GitHub UI)  
5. Confirm:
   - Version `test-1.0.1` exists on `REL`
   - Bug has **Fix Version** `test-1.0.1`
   - Actions run **sync-jira-versions** succeeded  

---

## 6. Differences from the PDF

| PDF | This implementation |
|---|---|
| Company Jira EA/ANY | Test site **`REL` only** |
| Tags `val-*` | **GitHub Releases only** (`release: published`), not every tag |
| Commit from Jira Development panel | **Merged PR title** in this repo |
| Epic-scoped JQL | All Done bugs with empty Fix Version |
| Separate product repos | Automation **lives in this repo** |

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Version create 401/403 | Check service account + `JIRA_CLOUD_ID` secrets |
| Fix Version not set | Bug not Done, or PR title missing key, or merge commit not in tag |
| Comment “no merged PR” | Merge a PR whose title contains the issue key in **this** repo |
| Affects empty on new bugs | Add the Automation rule in §3.2 |

---

## Related

- [Part2_PR_Jira_Key_Gate_Setup.md](Part2_PR_Jira_Key_Gate_Setup.md) — PR titles must cite existing keys (feeds this sync)  
- Plan PDF Part 2 — Fix / Affects Versions  
