# Part 1: Vehicle Serial Number Sync (MOM → EA)

**Site:** `https://atimotors-team-c7ja40wb.atlassian.net`  
**Date set up:** July 23, 2026  
**Approach:** Option A — trigger-based sync when a MOM ticket is created  
**Author:** Saandeep C Sijo

When a MOM ticket is created with a **Vehicle Serial No**, that value is added as a selectable option on the EA **Vehicle Serial Numbers** multi-select field. EA bugs can then link to one or more bots from a controlled list (consistent nomenclature).

---

## 1. Goal

| Problem | Solution |
|---|---|
| Support types serials inconsistently (`10K09` vs `10K 09`) | EA uses a managed multi-select option list |
| Options don’t auto-update from MOM | Jira Automation calls the REST API on MOM create |
| One bug may involve multiple bots | Field type is **Select List (multiple choices)** |

**Flow:**

```
MOM ticket created
  └─ Vehicle Serial No = "BOT 42"  (short text)
        │
        ▼
Jira Automation (Send web request)
  authenticated as service account
        │
        ▼
POST …/field/{fieldId}/context/{contextId}/option
        │
        ▼
EA field "Vehicle Serial Numbers" gains option "BOT 42"
        │
        ▼
EA Bug → pick one or more serials from the list
```

---

## 2. Important constraints

### 2.1 Team-managed vs global fields

EA and MOM are **team-managed** projects.

- Fields created *inside* a team-managed project are **project-scoped**.
- The options REST API does **not** work for project-scoped fields (returns “custom field was not found”).
- The EA target field must be a **global** custom field (created under Jira admin → Work items → Fields), then **added** into EA.

### 2.2 Need at least one company-managed project

On sites with only team-managed projects, global fields often **do not appear** under EA → Fields → Add fields.

Create (or keep) a helper company-managed project — we used:

| Key | Name | Purpose |
|---|---|---|
| `CMPY` | Company Managed Helper | Unlocks adding global fields into team-managed spaces |

It can stay empty.

### 2.3 Multi-select

A ticket can link to **multiple bots**, so EA uses **Select List (multiple choices)**.

### 2.4 Auth for Automation

Native Automation actions (create/edit issue) do **not** need an API token.  
**Send web request** to the field-options API **does** — use a **service account** (preferred) so the token is not tied to a personal login and can be limited to the test site.

---

## 3. Fields

### Source — MOM

| Property | Value |
|---|---|
| Name | Vehicle Serial No |
| ID | `customfield_10043` |
| Type | Short text |
| Scope | MOM only |
| Role | Free-text entry on MOM tickets |

### Target — EA (synced options)

| Property | Value |
|---|---|
| Name | Vehicle Serial Numbers |
| ID | `customfield_10046` |
| Type | Select List (multiple choices) |
| Scope | Global |
| Context ID | `10150` |
| Role | Canonical option list on EA bugs |

### Do not use for sync

| Name | ID | Why |
|---|---|---|
| Vehicle Serial Number (older) | `customfield_10042` | EA project-scoped checkboxes; options cannot be updated via REST |

---

## 4. One-time setup in Jira

### Step A — Create a company-managed helper project (if needed)

1. Create project → choose **company-managed** software  
2. Key example: `CMPY`  
3. No issues required — existence is enough

### Step B — Create the global multi-select field

1. Click the **gear** (Jira settings) → **Work items** (or **Issues**) → **Fields**  
2. **Create custom field**  
3. Type: **Select List (multiple choices)**  
4. Name: **Vehicle Serial Numbers**  
5. Keep a **global** context (all projects / all issue types)  
6. Do **not** create this field from inside EA project settings (that makes it project-scoped)

**Find the field ID and context ID** (needed for Automation):

1. Gear → Work items → Fields → find **Vehicle Serial Numbers**  
2. ••• → **Contexts and default value** (or **Configure**)  
3. Note the field id from the URL (`customfield_XXXXX`)  
4. Open the context / “Edit Configuration” — the URL contains the **context id**  
   - On this site: field `customfield_10046`, context `10150`

### Step C — Add the global field to EA

1. Open **EA** → **Project settings** / **Space settings**  
2. Open **Fields**  
3. Click **Add fields**  
4. Search **Vehicle Serial Numbers** (plural)  
5. Select it → **Add**  
6. Open **Issue types** → **Bug** (and any other types that need it)  
7. Confirm **Vehicle Serial Numbers** is on the layout  

You may still see the older **Vehicle Serial Number** checkbox field — leave it unused or remove it later to avoid confusion.

### Step D — MOM source field

1. Open **MOM** → Project settings → Issue types / Fields  
2. Ensure **Vehicle Serial No** (short text) is on the create form for the work types you use (e.g. Task)

---

## 5. Service account setup (for Automation auth)

Use a service account instead of a personal API token so:

- Access is not tied to one employee’s login  
- The token can be scoped and rotated independently  
- On this setup, the account is limited to the **test site** (not company Jira)

Official docs:

- [Understand service accounts](https://support.atlassian.com/user-management/docs/understand-service-accounts/)  
- [Manage API tokens for service accounts](https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/)

### 5.1 Create the service account (org admin)

1. Go to [admin.atlassian.com](https://admin.atlassian.com)  
2. Select the organization  
3. **Directory** → **Service accounts** → **Create a service account**  
4. Name (e.g. `automation`) + optional description  
5. Assign **Jira** app access for the **test site only**  
6. **Create**  

Atlassian generates an email like:

`automation-keps7st7ec@serviceaccount.atlassian.com`  

(email cannot be changed later). Service accounts cannot log into the Jira UI — API only.  
Free limit: **5 service accounts per org** (more requires Guard).

### 5.2 Grant Jira permissions on the test site

Two layers both matter:

| Layer | What to set | Needed for |
|---|---|---|
| **Product / groups** | e.g. `jira-admins-…` on the test site, or Administer Jira | Managing field options via REST |
| **Space access** | Add the service account to **MOM** and **EA** | Project membership (team-managed spaces often need an explicit invite) |

**Recommended for this sync:**

1. Add the service account to the site’s **Jira admins** group (or equivalent **Administer Jira**), so it can create field options  
2. **EA** → Project settings → **Access** → add service account as **Administrator**  
3. **MOM** → Project settings → **Access** → add service account (Member or Administrator)

Verified on this test site:

| Space | Access |
|---|---|
| EA | Full issue + project admin |
| MOM | Full issue access (create/edit/delete/browse) |
| Company Jira (`ati-motors`) | **No** — token rejected |

Minimum required for the sync rule itself: ability to **POST field options**. Space membership on MOM/EA is still recommended so the account is clearly scoped and auditable.

### 5.3 Create an API token for the service account

1. [admin.atlassian.com](https://admin.atlassian.com) → **Directory** → **Service accounts**  
2. Open the account → **Create credentials** → **API token**  
3. Name + expiry (1–365 days)  
4. Select **scopes** (include whatever is needed to manage Jira configuration / field options; also read/write if you expand later)  
5. **Create** → copy the token once (it cannot be viewed again)

**Do not commit the raw token to git or this doc.** Store it in a password manager / secrets store.

### 5.4 How service-account tokens must be called

Scoped service-account tokens do **not** work against the normal site URL:

```text
https://atimotors-team-c7ja40wb.atlassian.net/rest/api/3/...   ❌ (401 / not accepted)
```

Use the **API gateway** with the site **Cloud ID**:

```text
https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/...
```

| Site | Cloud ID |
|---|---|
| Test (`atimotors-team-c7ja40wb`) | `994ccf9c-4f0e-43b4-9172-438a4bd06cc8` |

Find Cloud ID: open `https://<yoursite>.atlassian.net/_edge/tenant_info`

Auth that works with this token:

- `Authorization: Basic <base64(service_account_email:api_token)>` ← use this in Automation  
- or `Authorization: Bearer <api_token>` (fine in scripts)

---

## 6. Automation rule (MOM → EA options)

Configured under **MOM** → Project settings → **Automation**.

### Rule configuration

| Setting | Value |
|---|---|
| Name | e.g. `Sync Vehicle Serial → EA options` |
| Trigger | **Work item created** |
| Condition | **Vehicle Serial No** is not empty |
| Action | **Send web request** |

**Optional but recommended:** a second rule (or additional trigger) for **Field value changed** → Vehicle Serial No, so serials filled in after create also sync.

### Send web request

| Setting | Value |
|---|---|
| Web request URL | See below (must end with `/option`) |
| HTTP method | `POST` |
| Wait for response | **Yes** |
| Continue on non-2xx / error | **Yes** (duplicates return HTTP 400) |

**URL (this test site):**

```text
https://api.atlassian.com/ex/jira/994ccf9c-4f0e-43b4-9172-438a4bd06cc8/rest/api/3/field/customfield_10046/context/10150/option
```

**Headers:**

| Header | Value |
|---|---|
| `Authorization` | `Basic <base64(service_account_email:api_token)>` |
| `Content-Type` | `application/json` |

**Body (custom data):**

```json
{
  "options": [
    {
      "disabled": false,
      "value": "{{issue.customfield_10043}}"
    }
  ]
}
```

### Generate the Authorization header

1. Take the service account email + API token  
2. Encode `email:token` as Base64, then prefix with `Basic ` (space after `Basic`)  

Example (local):

```bash
python3 -c "import base64; print('Basic ' + base64.b64encode(b'SERVICE_EMAIL:API_TOKEN').decode())"
```

3. Paste the **full** string as the Authorization header value  
4. Do **not** use only the raw token, and do not omit `Basic `  
5. Avoid a conflicting separate “Authentication” username/password block in the web request action if it overrides headers  

### Duplicate options

If the serial already exists, Jira returns HTTP 400 (“option value must be unique”). That is expected — keep **continue on error** enabled. Options on the field are always unique.

### Manual options

Admins can still add/remove options manually under Fields → Vehicle Serial Numbers → context options. Manual and automation-synced values share the same list.

---

## 7. Day-to-day use

### Add a new serial

1. **MOM** → **Create**  
2. Set **Vehicle Serial No** to the exact canonical string (e.g. `10K 09`)  
3. Create the ticket  
4. Wait a few seconds  
5. Optional: Automation → **Audit log** to confirm the web request succeeded (HTTP 200)  

### File an EA bug against bots

1. **EA** → **Create** → **Bug**  
2. Open **Vehicle Serial Numbers**  
3. Select one or more options  
4. Create  

---

## 8. How we verified it

1. Created MOM tickets with new serials (e.g. `AUTO 173649` on **MOM-13**)  
2. Confirmed Automation audit log showed a successful web request  
3. Confirmed the new value appeared on `customfield_10046` options within a few seconds  
4. Confirmed EA Bug create can pick the synced options  

---

## 9. IDs cheat sheet (this test site)

| Item | Value |
|---|---|
| Site | `atimotors-team-c7ja40wb.atlassian.net` |
| Cloud ID | `994ccf9c-4f0e-43b4-9172-438a4bd06cc8` |
| MOM | Team-managed |
| EA | Team-managed |
| Helper project | `CMPY` (company-managed) |
| MOM serial field | `customfield_10043` |
| EA options field | `customfield_10046` |
| EA options context | `10150` |
| Service account (example) | `automation` / `automation-keps7st7ec@serviceaccount.atlassian.com` |
| Add-option URL | `https://api.atlassian.com/ex/jira/994ccf9c-4f0e-43b4-9172-438a4bd06cc8/rest/api/3/field/customfield_10046/context/10150/option` |
| Older unused EA field | `customfield_10042` |

If you recreate the field on another site, replace Cloud ID, field id, and context id in the Automation URL.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Only see “Vehicle Serial Number” (singular / checkboxes) | Using project-local field, or global field not added | EA → **Fields** → **Add fields** → **Vehicle Serial Numbers** |
| Global field missing from Add fields | No company-managed project on the site | Keep `CMPY` (or any classic project) |
| Automation **405** Method Not Allowed | URL missing `/option` (ends at `/context/10150/`) | Append `/option` to the URL |
| Automation **401** | Wrong auth / site URL with scoped token / missing `Basic ` | Use gateway URL + `Basic` header from service account email:token |
| Automation **404** | Wrong field/context, or project-scoped field | Use global field + correct context id |
| Automation **400** “must be unique” | Option already exists | Expected; continue on error |
| Service account can’t create/browse MOM or EA issues | Not added under Project **Access** | Invite the service account as Member/Admin on that space |
| Personal API token reaches company Jira too | Same Atlassian user is on both sites | Prefer service account limited to the test site only |
| New serial not in EA dropdown | Rule failed or delayed | Check Automation **Audit log**; refresh create screen |

---

## 11. Suggested cleanups / follow-ups

1. Add a **Field value changed** trigger for Vehicle Serial No  
2. Remove or hide old EA field `customfield_10042` to avoid confusion  
3. Make **Vehicle Serial Numbers** required on EA Bug  
4. Add the same global field to other projects (e.g. ANY) via Fields → Add fields  
5. On production Jira, recreate the global field + service account + rule and update the IDs in this doc  
6. Rotate the service account API token on a schedule; update the Automation Authorization header when it expires  

---

## Related plan

See `Jira_Automation_Plan_SoftwareBugs.md.pdf` — **Part 1**, Option A, changed from scheduled sync to **trigger on MOM create**.
