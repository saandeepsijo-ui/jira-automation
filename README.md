# jira-automation

Automation and CI helpers for ATI Motors Jira workflows.

## Contents

| Area | Doc |
|---|---|
| Part 1 — MOM → EA vehicle serial options sync | [Part1_Vehicle_Serial_Sync_Setup.md](Part1_Vehicle_Serial_Sync_Setup.md) |
| Part 2 — PR keys, Affects Version, GitHub Release → Fix Version | [Part2_Setup.md](Part2_Setup.md) |

## CI

- **`jira-pr-title`** — PR title must contain Jira keys that exist on the test site  
- **`sync-jira-versions`** — on **GitHub Release published**: create Jira version in `REL` and set Fix Version on Done bugs linked by merged PR titles  
