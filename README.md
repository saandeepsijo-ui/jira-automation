# jira-automation

Automation and CI helpers for ATI Motors Jira workflows.

## Contents

| Area | Doc |
|---|---|
| Part 1 — MOM → EA vehicle serial options sync | [Part1_Vehicle_Serial_Sync_Setup.md](Part1_Vehicle_Serial_Sync_Setup.md) |
| Part 2 — PR title must reference existing Jira tickets | [Part2_PR_Jira_Key_Gate_Setup.md](Part2_PR_Jira_Key_Gate_Setup.md) |
| Part 2 — Affects Version + tag → Fix Version (`REL`) | [Part2_Versions_And_Tags_Setup.md](Part2_Versions_And_Tags_Setup.md) |

## CI

- **`jira-pr-title`** — PR title must contain Jira keys that exist on the test site
- **`sync-jira-versions`** — on **GitHub Release published**: create Jira version in `REL` and set Fix Version on Done bugs linked by merged PR titles
release-smoke 2026-07-24T14:08:43+05:30
