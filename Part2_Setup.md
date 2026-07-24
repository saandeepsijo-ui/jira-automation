# Part 2: PR Jira keys, Affects Version & GitHub Release → Fix Version

**Site:** `https://atimotors-team-c7ja40wb.atlassian.net`  
**Versions project:** `REL` (Release Tracking) — **company-managed**  
**Repo:** [saandeepsijo-ui/jira-automation](https://github.com/saandeepsijo-ui/jira-automation)  
**Author:** Saandeep C Sijo

This is the single setup guide for Part 2 (stricter than the plan PDF’s regex-only PR check, and Release-based rather than every git tag).

---

## 1. Architecture (what we implemented)

```
PR opened / title edited
  → GitHub Action jira-pr-title
  → extract KEY-123 from title (title only; multiple OK)
  → each key must EXIST on test Jira
  → fail check / block merge if missing

Bug created in REL
  → Affects Version = current cycle (e.g. val-26.7)
  → (Jira Automation rule — configure in UI)

PR titled "REL-12: fix …" merges
  → …

GitHub Release published (tag e.g. release-smoke-140949)
  → Action sync-jira-versions
  → create Jira version named as the release tag (released=true)
  → for Done bugs with empty Fix Version:
       find merged PRs in this repo whose TITLE contains the issue key
       if merge commit is in that tag → set Fix Version
       else comment on the issue
```

**Important:** A plain `git tag` / `git push --tags` does **not** sync to Jira. Only a **published GitHub Release** does.

### Affects vs Fix Version

| Field | Meaning | When set |
|---|---|---|
| **Affects Version** | Broken / found while testing this cycle | Bug **create** → e.g. `val-26.7` |
| **Fix Version** | Shipped in this **GitHub Release** | Release **published** → tag name |

Both pickers use the same project version list. A new release version therefore appears as an option under **Affects versions** and **Fix versions**.

---

## 2. Why project `REL`?

Team-managed `EA` does not handle Releases/Versions reliably via REST.  
`REL` is company-managed on the test site for this automation.

| Item | Value |
|---|---|
| Key | `REL` |
| Name | Release Tracking |
| Style | classic (company-managed) |
| Bootstrap Affects Version | `val-26.7` (unreleased) |
| Service account | `automation` (Administrators) |

---

## 3. A — PR title must reference existing Jira tickets

### Goal

| Problem | Solution |
|---|---|
| PRs merge without a linked ticket | Required CI check on PR title |
| Fake keys like `EA-99999` | Each key must **exist** on Jira |
| One PR may fix several tickets | All keys in the title are validated |

### Files

| Path | Purpose |
|---|---|
| [`.github/workflows/check-jira-pr-title.yml`](.github/workflows/check-jira-pr-title.yml) | PR events |
| [`scripts/check_jira_pr_title.py`](scripts/check_jira_pr_title.py) | Parse title + verify keys |

### GitHub setup (one-time)

**Secrets / variables** (Settings → Secrets and variables → Actions):

| Name | Type | Value |
|---|---|---|
| `JIRA_EMAIL` | secret | Service account email |
| `JIRA_API_TOKEN` | secret | API token |
| `JIRA_CLOUD_ID` | variable | `994ccf9c-4f0e-43b4-9172-438a4bd06cc8` |
| `JIRA_BASE` | variable | `https://atimotors-team-c7ja40wb.atlassian.net` (fallback) |
| `JIRA_PROJECT` | variable | `REL` (used by Fix Version sync) |

Scoped service-account tokens need `JIRA_CLOUD_ID` (API gateway). Browse access is enough for the PR check; version sync needs project admin / version create on `REL`.

**Branch protection** on `main`:

1. Require status checks to pass  
2. Require check name: **`jira-pr-title`**

### PR title conventions

**Good:** `REL-3: fix …` · `MOM-13 EA-5: multi` · `[REL-2] Improve logging`  

**Bad:** no key · nonexistent key · lowercase `mom-13`  

Regex: `\b([A-Z][A-Z0-9]+-\d+)\b`

### Local dry-run

```bash
export JIRA_CLOUD_ID='994ccf9c-4f0e-43b4-9172-438a4bd06cc8'
export JIRA_EMAIL='…'
export JIRA_API_TOKEN='…'
export PR_TITLE='REL-3: test'
python3 scripts/check_jira_pr_title.py
```

---

## 4. B — Affects Version on Bug create

### Bootstrap (done on test site)

Version **`val-26.7`** exists on `REL`, unreleased.

New cycle later: **REL → Releases** → create version, leave unreleased.

### Jira Automation rule (manual UI step)

Under **REL → Project settings → Automation**:

| Setting | Value |
|---|---|
| Name | `Default Affects Version on Bug` |
| Trigger | Work item created |
| Condition | Issue type = **Bug** |
| Action | Edit → **Affects versions** → `val-26.7` (or latest unreleased) |

Until this rule exists, set Affects manually / via API: `"versions": [{"name": "val-26.7"}]`.

---

## 5. C — GitHub Release → Jira version + Fix Version

### Files

| Path | Role |
|---|---|
| [`.github/workflows/sync-jira-versions-on-tag.yml`](.github/workflows/sync-jira-versions-on-tag.yml) | `on: release: types: [published]` |
| [`scripts/sync_jira_versions_on_tag.py`](scripts/sync_jira_versions_on_tag.py) | Create version + PR-based Fix Version |

### Trigger

| Event | Syncs to Jira? |
|---|---|
| GitHub **Release** published | **Yes** — version name = `release.tag_name` |
| Git tag push only | **No** |
| Draft release | **No** (until published) |
| Pre-release published | **Yes** |

### Behaviour (automatic Fix Version from PR titles)

1. Create Jira version for the release tag in `REL` (`released: true`); skip if it already exists  
2. JQL: `project = REL AND issuetype = Bug AND statusCategory = Done AND fixVersion is EMPTY`  
3. For each issue key → GitHub search for **merged PRs in this repo** with that key in the **title**  
4. Take `merge_commit_sha` → `git tag --contains <sha>`  
5. If current release tag is listed → **add Fix Version**  
6. If PR exists but commit not in tag → **comment** (cherry-pick / deferred)  
7. If no merged PR → **comment** (Fix Version left empty)

This is PR-title based (not Smart Commits / Jira Development panel).

---

## 6. Verified on the test site

| Test | Result |
|---|---|
| PR title gate (exists / missing / fake key) | Pass / fail as designed; branch protection requires `jira-pr-title` |
| **REL-2** + tag era smoke | Fix Version set from merged PR title after version sync |
| **GitHub Release** `release-smoke-140949` published | Workflow **success** |
| Jira version created | `release-smoke-140949` present on `REL` |
| **REL-3** Fix Version | Set to `release-smoke-140949` (PR #4 title contained `REL-3`) |
| Affects / Fix pickers (`editmeta`) | Both lists include `release-smoke-140949` |

Release example: https://github.com/saandeepsijo-ui/jira-automation/releases/tag/release-smoke-140949

---

## 7. Smoke test (repeat anytime)

1. Create Bug in `REL` with Affects `val-26.7` → Done  
2. PR titled `REL-N: …` → merge  
3. Publish release:  
   `gh release create <tag> --target main --title "<tag>" --notes "…"`  
4. Confirm version on `REL`, Fix Version on the bug, Actions **sync-jira-versions** green  

---

## 8. Plan: one-time backfill for previous GitHub Releases

Ongoing sync only runs when a **new** release is published. Older GitHub Releases (and older Done bugs) need a **one-time backfill**.

### Goal

For each existing GitHub Release (or a chosen list of tags):

1. Ensure a Jira version with that name exists on `REL`  
2. For Done bugs still missing Fix Version, apply the same PR-title + `git tag --contains` rules as the live workflow  

### Suggested approach

1. **Inventory releases** in this repo:  
   `gh release list`  
   Decide which ones count as real product releases (skip probes like `release-smoke-*` if desired).

2. **Add a backfill script** (proposed path: `scripts/backfill_jira_fix_versions.py`) that:
   - Accepts `--tags tag1,tag2` **or** `--all-releases`  
   - For each tag (oldest → newest recommended):
     - `ensure_version(REL, tag)` (same as live script)  
     - Reuse the live script’s logic: search Done bugs with empty Fix Version → matched merged PRs → `git tag --contains` → set Fix Version or comment  
   - Supports `--dry-run` (log only, no Jira writes)

3. **Run once locally or via a workflow_dispatch job** with full git history (`fetch-depth: 0`) and the same secrets/vars as production.

4. **Order matters:** process tags chronologically so a bug fixed in an older release is stamped with that release, not a later one (once Fix Version is set, later tags skip that bug because `fixVersion is EMPTY` no longer matches).

5. **Idempotent:** re-running skips bugs that already have a Fix Version; version create is already “exists → continue”.

6. **Safety:**
   - Dry-run first; review the log  
   - Optionally restrict with `--since 2026-01-01` or an allowlist of tags  
   - Do not backfill Affects Version historically unless product explicitly wants it (separate, usually manual)

7. **After backfill:** rely on the live `release: published` workflow only; keep the backfill script for rare re-runs (e.g. new project cutover).

### Out of scope for backfill (unless requested later)

- Creating GitHub Releases for tags that never had a Release object  
- Company Jira / EA / ANY  
- Changing already-set Fix Versions  

---

## 9. Differences from the plan PDF

| PDF | This implementation |
|---|---|
| Regex-only PR title check | Key must **exist** on Jira |
| Company EA/ANY | Test site **`REL`** |
| Every / `val-*` tags | **GitHub Releases only** |
| Commit via Development panel | **Merged PR title** in this repo |
| Epic-scoped JQL | All Done bugs with empty Fix Version |
| Product app repos | Automation **in this repo** |

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| PR check never runs | Workflow on default branch; open new PR |
| PR check 401 / secrets error | Set `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_CLOUD_ID` |
| Key exists in UI but check MISS | Grant bot Browse on that project |
| Merge allowed when check red | Require `jira-pr-title` in branch protection |
| Tag pushed but no Jira version | Publish a **Release**, not only a tag |
| Fix Version not set | Bug not Done; PR title missing key; merge commit not in tag |
| Comment “no merged PR” | Merge a PR in **this** repo with the key in the title |
| Affects empty on new bugs | Add Automation rule in §4 |
| Old releases missing as versions | Run the §8 backfill plan |

---

## Related

- Plan PDF: `Jira_Automation_Plan_SoftwareBugs.md.pdf` — Part 2  
- Part 1: [Part1_Vehicle_Serial_Sync_Setup.md](Part1_Vehicle_Serial_Sync_Setup.md)  
