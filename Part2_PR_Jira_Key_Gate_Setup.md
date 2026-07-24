# Part 2 (slice): PR title must reference existing Jira tickets

**GitHub check:** `jira-pr-title`  
**Jira site (current):** `https://atimotors-team-c7ja40wb.atlassian.net`  
**Scope:** PR **title** only — commits and body are ignored. Multiple keys allowed; every key must exist.

When a pull request is opened or its title is edited, GitHub Actions extracts Jira keys from the title (e.g. `MOM-13`, `EA-5`) and calls the Jira REST API. The check fails (and merge can be blocked) if there are no keys or any key does not exist.

---

## 1. Goal

| Problem | Solution |
|---|---|
| PRs merge without a linked Jira ticket | Required CI check on PR title |
| Fake keys like `EA-99999` would pass a regex-only check | Each key must **exist** on Jira |
| One PR may fix multiple tickets | All keys in the title are validated |

```
PR opened / title edited
        │
        ▼
GitHub Action: jira-pr-title
        │
        ▼
Extract KEY-123 from title (one or more)
        │
        ▼
GET /rest/api/3/issue/{key}  (test Jira)
        │
        ├── all exist → check passes
        └── none / any missing → check fails → merge blocked
```

This is stricter than the PDF Part 2b sample (regex-only). Keys in PR titles also feed **Fix Version sync** for project `REL` when tags are pushed — see [Part2_Versions_And_Tags_Setup.md](Part2_Versions_And_Tags_Setup.md).

---

## 2. Files in this repo

| Path | Purpose |
|---|---|
| [`.github/workflows/check-jira-pr-title.yml`](.github/workflows/check-jira-pr-title.yml) | Runs on PR events |
| [`scripts/check_jira_pr_title.py`](scripts/check_jira_pr_title.py) | Parse title + verify keys via Jira |

---

## 3. One-time GitHub setup

### 3.1 Repository secrets

In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret / variable | Value |
|---|---|
| Secret `JIRA_EMAIL` | Service account email (e.g. `automation-…@serviceaccount.atlassian.com`) |
| Secret `JIRA_API_TOKEN` | API token for that account |
| Variable `JIRA_CLOUD_ID` | Test site Cloud ID: `994ccf9c-4f0e-43b4-9172-438a4bd06cc8` (required for scoped service-account tokens) |
| Variable `JIRA_BASE` | Optional fallback site URL if not using Cloud ID: `https://atimotors-team-c7ja40wb.atlassian.net` |

The Jira account needs **Browse** access to issues (and membership on projects it must see). Administer Jira is not required for this check.

**Scoped service-account tokens** must use the API gateway (`JIRA_CLOUD_ID`). Classic user tokens can use `JIRA_BASE` alone.
### 3.2 Branch protection (block merge)

1. **Settings → Branches → Add branch protection rule** (e.g. `main`)  
2. Enable **Require status checks to pass before merging**  
3. Search and require: **`jira-pr-title`**  
4. Save  

Until this is set, a failed check is visible but merge is still allowed.

### 3.3 Service account note

Prefer a **test-site-only** service account. Set `JIRA_CLOUD_ID` so the check uses `https://api.atlassian.com/ex/jira/{cloudId}/…` (required for scoped tokens).

For company Jira later: change `JIRA_CLOUD_ID` / secrets to that site; keep the same workflow.

---

## 4. PR title conventions

**Good**

```text
MOM-13: sync vehicle serial options
EA-5 MOM-3: fix navigation timeout
[MOM-13] Improve logging
```

**Bad**

```text
fix stuff                    # no key
EA-99999: ghost ticket       # key does not exist
mom-13: lowercase project    # not matched (keys must be uppercase PROJECT-123)
```

Regex used: `\b([A-Z][A-Z0-9]+-\d+)\b`

---

## 5. Local dry-run

```bash
export JIRA_BASE='https://atimotors-team-c7ja40wb.atlassian.net'
export JIRA_EMAIL='your-bot@...'
export JIRA_API_TOKEN='...'
export PR_TITLE='MOM-13: test'
python3 scripts/check_jira_pr_title.py
```

Exit `0` = pass, `1` = fail.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Check never runs | Workflow not on default branch / path wrong | Push workflow to default branch; open a new PR |
| Check fails with secrets error | Missing `JIRA_EMAIL` / `JIRA_API_TOKEN` | Add repo secrets |
| Check fails 401 | Bad token or wrong email | Rotate token; confirm account can browse test site |
| Key exists in UI but check says MISS | Bot cannot see the project | Add bot to the project / grant Browse |
| Merge still allowed when red | Branch protection not requiring the check | Require `jira-pr-title` on the branch |
| Want company Jira later | Point `JIRA_BASE` + secrets at `ati-motors.atlassian.net` | Update variable/secrets; keep same workflow |

---

## 7. Out of scope (later Part 2)

- Git tag → Jira Fix Version creation  
- Affects Version automation  
- Scanning commit messages or PR body  
- Restricting keys to EA / ANY only  

---

## Related

- Plan PDF: `Jira_Automation_Plan_SoftwareBugs.md.pdf` — Part 2b PR title convention  
- Part 1 doc: `Part1_Vehicle_Serial_Sync_Setup.md`
