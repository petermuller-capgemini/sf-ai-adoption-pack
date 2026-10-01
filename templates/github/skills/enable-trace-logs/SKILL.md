---
name: enable-trace-logs
description: Enable Apex debug trace flags for one or more users in a Salesforce sandbox. Handles DebugLevel lookup, existing flag cleanup, and TraceFlag creation via Tooling API. Supports named users, guest users, and AutomatedProcess.
---

# Enable Trace Logs

Enable Apex debug trace flags on a target org so that execution logs are captured for the right user(s).

## Invocation

```
/enable-trace-logs <org-alias>
/enable-trace-logs guest <org-alias>          ← traces the Experience Cloud guest user & integration user
/enable-trace-logs <name-or-id> <org-alias>   ← traces a specific named user
```

If arguments are not supplied, ask for the org alias and whether to trace the guest users or a specific user.

---

## Step 1 — Identify which user(s) to trace

The user to trace depends on what code path you're debugging:

| Code path | Runs as |
|---|---|
| LWC → Apex controller (Experience Cloud guest page) | `{{SITE_NAME}} Site Guest User` |
| Loopback API callouts from guest page | `{{APEX_PREFIX}}_Guest_Booking_Integration` user |
| Anonymous Apex (`sf apex run`) | Your authenticated CLI user |
| Batch / Queueable Apex | `Automated Process` system user |
| Platform Event trigger (`after insert`) | User set in `PlatformEventSubscriberConfig` |

### Find the guest user and integration user

```bash
sf data query --target-org <org> \
  --query "SELECT Id, Name, Username FROM User WHERE Name IN ('{{SITE_NAME}} Site Guest User','{{APEX_PREFIX}}_Guest_Booking_Integration') ORDER BY Name"
```

Expected results on `<org-alias>`:

| Name | Id |
|---|---|
| {{APEX_PREFIX}}_Guest_Booking_Integration | `<user-id-1>` |
| {{SITE_NAME}} Site Guest User | `<user-id-2>` |

### Find the AutomatedProcess user

```bash
sf data query --target-org <org> \
  --query "SELECT Id, Name FROM User WHERE Name = 'Automated Process' LIMIT 1"
```

### Find a named user

```bash
sf data query --target-org <org> \
  --query "SELECT Id, Name, Username FROM User WHERE Name LIKE '%<name>%' LIMIT 5"
```

---

## Step 2 — Find an existing DebugLevel (Tooling API)

`DebugLevel` and `TraceFlag` are Tooling API objects — always add `--use-tooling-api`.

```bash
sf data query --target-org <org> --use-tooling-api \
  --query "SELECT Id, DeveloperName FROM DebugLevel WHERE DeveloperName = 'SFDC_DevConsole' LIMIT 1"
```

If no `SFDC_DevConsole` level exists, create one:

```bash
sf data create record --target-org <org> --use-tooling-api \
  --sobject DebugLevel \
  --values "DeveloperName=SFDC_DevConsole MasterLabel=SFDC_DevConsole ApexCode=FINEST ApexProfiling=INFO Callout=INFO Database=INFO System=DEBUG Validation=INFO Visualforce=INFO Workflow=INFO"
```

Note the returned Id — use it as `DebugLevelId` in Step 4.

---

## Step 3 — Delete any existing trace flags for the target users

Running duplicate trace flags causes silent log loss. Always clean up first.

```bash
sf data query --target-org <org> --use-tooling-api \
  --query "SELECT Id FROM TraceFlag WHERE TracedEntityId IN ('<userId1>','<userId2>') AND LogType = 'USER_DEBUG'"
```

If any records are returned, delete them:

```bash
sf data delete record --target-org <org> --use-tooling-api \
  --sobject TraceFlag --record-id <flagId>
```

---

## Step 4 — Create TraceFlag(s)

`ExpirationDate` cannot exceed 24 hours from now. Generate an expiry timestamp:

```bash
# macOS
EXPIRY=$(date -u -v+24H "+%Y-%m-%dT%H:%M:%S.000+0000")
START=$(date -u "+%Y-%m-%dT%H:%M:%S.000+0000")
```

Create a flag for each user:

```bash
sf data create record --target-org <org> --use-tooling-api \
  --sobject TraceFlag \
  --values "TracedEntityId=<userId> DebugLevelId=<debugLevelId> LogType=USER_DEBUG StartDate=$START ExpirationDate=$EXPIRY"
```

Repeat for each user. Note the returned `Id` for reference.

### Guest user one-liner (example)

```bash
EXPIRY=$(date -u -v+24H "+%Y-%m-%dT%H:%M:%S.000+0000")
START=$(date -u "+%Y-%m-%dT%H:%M:%S.000+0000")
DL_ID=<debug-level-id>   # SFDC_DevConsole on <org-alias>

# Experience Cloud guest user
sf data create record --target-org <your-username>.<org-alias> --use-tooling-api \
  --sobject TraceFlag \
  --values "TracedEntityId=<guest-user-id> DebugLevelId=$DL_ID LogType=USER_DEBUG StartDate=$START ExpirationDate=$EXPIRY"

# Integration user
sf data create record --target-org <your-username>.<org-alias> --use-tooling-api \
  --sobject TraceFlag \
  --values "TracedEntityId=<integration-user-id> DebugLevelId=$DL_ID LogType=USER_DEBUG StartDate=$START ExpirationDate=$EXPIRY"
```

---

## Step 5 — Reproduce the issue and retrieve the log

### Stream logs in real time

```bash
sf apex tail log --target-org <org>
```

### List recent logs

```bash
sf apex list log --target-org <org> 2>/dev/null
```

### Download a specific log

```bash
sf apex get log --target-org <org> --log-id <logId> 2>/dev/null
```

### Filter for the relevant lines

```bash
sf apex get log --target-org <org> --log-id <logId> 2>/dev/null \
  | grep -E "USER_DEBUG|CALLOUT_REQUEST|CALLOUT_RESPONSE|EXCEPTION" | head -60
```

---

## Step 6 — Check the daily log limit

Orgs cap total debug log volume per day. When hit, new logs are silently dropped.

```bash
sf data query --target-org <org> \
  --query "SELECT COUNT() FROM ApexLog"
```

If the count is high, delete old logs:

```bash
sf data query --target-org <org> --query "SELECT Id FROM ApexLog LIMIT 200" --json \
  | python3 -c "import sys,json; [print(r['Id']) for r in json.load(sys.stdin)['result']['records']]" \
  | xargs -I{} sf data delete record --target-org <org> --sobject ApexLog --record-id {}
```

---

## Notes

- **`DebugLevel` and `TraceFlag` are Tooling API objects** — every query or DML against them requires `--use-tooling-api`. Omitting it gives "entity not found" errors.
- **Login As and trace flags:** when an admin is logged in as another user, Apex executes as the impersonated user. Set the trace flag on the impersonated user's Id, not the admin's.
- **Guest page LWC calls run as the Experience Cloud guest user**, not the backend integration user. The integration user runs the loopback API callouts made from the guest page. Trace both when debugging the full guest journey.
- **Batch/Queueable runs as AutomatedProcess** — a trace flag on your own user won't capture the batch body. Set a separate flag for the AutomatedProcess user.
- **Platform event triggers** run as the user set in `PlatformEventSubscriberConfig` (a dedicated system integration user), not AutomatedProcess.
- All `sf` CLI commands require `dangerouslyDisableSandbox: true` in Bash tool calls — the SF CLI writes logs to `~/.sf/` which is outside the sandbox write allowlist.
- If your workflow routes changes through a {{CICD_TOOL}} commit UI, do not run `git commit` or `git push` directly.
