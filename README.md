# jira-automation

Automation and CI helpers for ATI Motors Jira workflows.

## Contents

| Area | Doc |
|---|---|
| Part 1 — MOM → EA vehicle serial options sync | [Part1_Vehicle_Serial_Sync_Setup.md](Part1_Vehicle_Serial_Sync_Setup.md) |
| Part 2 (slice) — PR title must reference existing Jira tickets | [Part2_PR_Jira_Key_Gate_Setup.md](Part2_PR_Jira_Key_Gate_Setup.md) |

## CI

Pull requests run **`jira-pr-title`**: the PR title must contain one or more Jira issue keys that exist on the configured Jira site. See the Part 2 doc for secrets and branch protection.

<!-- ci probe -->
