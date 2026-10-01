---
name: dev-code-review
description: Salesforce secure code review assistant. Analyse modified or staged Apex, LWC, Trigger, and Flow files against org standards, SAD/FDS, and Work Item acceptance criteria. Runs static analysis (sf code-analyzer), IDOR scanner, and Apex tests. Produces structured findings, suggested Conventional Commit message, and {{CICD_TOOL}} commit instructions. Two modes: Test Classes (Mode A) vs Regular Files (Mode B) with auto-detection. Use whenever the user asks to review code, check a PR, validate changes before commit, or audit a work item's implementation.
---

# Salesforce Secure Code Review Skill

## Quick Start

1. Load the full review checklist from `references/checklist.md`
2. Ask the single multi-part question in §3 before starting
3. Auto-detect Mode A (test files) or Mode B (regular files)
4. Run quality gates (§8) and post findings using the output template (§9)

---

## 1. Input Resolution

| Field | Resolution order |
|---|---|
| Work Item | Work item ID from user → your work item tracker (e.g. {{WORK_ITEM_TOOL}}), if an MCP/tool integration is available → otherwise ask the user for the ID/details |
| Developer name | User-supplied → `git config user.name` → parse `user.email` → ask |
| Project | Conversation context → ask once |
| Date | Today `YYYY-MM-DD` |
| Test metrics | `sf apex run test --json` output |

---

## 2. Mode Detection

- **Mode A** — all discovered files match `*Test.cls`, `*Tests.cls`, or contain `@IsTest`
- **Mode B** — any non-test file present (Apex, Trigger, LWC, Flow)
- **Mixed** — treat non-test files as Mode B; apply Mode A rules to any test files in scope

---

## 3. Initial Questions (single message)

Ask all at once:

> 1. Review **all modified files** or **only staged files**?
> 2. Any checks to skip this pass (linting, accessibility, tests)?
> 3. Any extra context from SAD/FDS/Work Item (sections, edge cases, limits)?

---

## 4. Load References

Before reviewing, load the references file that matches what is in scope:

```
.github/skills/dev-code-review/references/checklist.md  ← always load
.github/instructions/apex.instructions.md               ← when Apex in scope
.github/instructions/lwc.instructions.md                ← when LWC in scope
.github/instructions/trigger.instructions.md            ← when Triggers in scope
.github/instructions/flow.instructions.md               ← when Flows in scope
```

---

## 5. Cross-Cutting Rules (ALL files)

### Security & Data Access
- CRUD/FLS: `WITH USER_MODE` in SOQL or programmatic checks
- No dynamic SOQL built from user input without binding/escaping
- LWC: route FLS-sensitive reads via Apex (user mode) or LDS
- Triggers must delegate to handler/service — no logic in trigger file

### Performance & Limits
- No SOQL/DML in loops — collect IDs, query/update outside loops
- **Transitive SOQL/DML in loops (same severity as direct)**: if a method that issues SOQL or DML is *called* from inside a loop, that is an identical governor-limit violation. Trace one level deep: check whether any method invoked inside a loop body contains a SOQL/DML statement. If so, raise a **Blocking** finding and recommend refactoring the callee to accept a collection instead of a single record.
- Flow Get Records: only needed fields

### Maintainability & Logging
- `{{LOGGER_CLASS}}` via `{{LOGGER_FACTORY}}.getFactory()` — no `System.debug()`
- No hardcoded IDs or URLs — use Custom Metadata, Labels
- No secrets in code — use Named Credentials
- No hardcoded cron/schedule strings — use Custom Metadata for schedule configuration
- Call `logger.publishBatchedLogEvents()` in `finally` for batched loggers

### Security — Custom Permissions
- `@AuraEnabled` methods gating privileged/destructive actions must verify the same custom permission **server-side** via `FeatureManagement.checkPermission()` — client-side LWC `hasCustomPermission` is bypassable — **BLOCKING** (OWASP A01)
- Permission-set name string literals shared across 3+ classes must be constants — **MAJOR**

### Async Apex (Batch & Queueable)
- **Batch duplicate-run guard (MAJOR)**: Query `AsyncApexJob` for a running instance before enqueuing; missing guard on shared records risks double-processing
- **Duplicate-run check placement (MAJOR)**: Guard must be in `execute(SchedulableContext ctx)`, not the constructor
- **Self-chaining batch (MAJOR)**: `finish()` calling `Database.executeBatch(this/same class)` when a Schedulable already covers re-runs is redundant and risks double-processing
- **Queueable list size cap (MAJOR)**: A Queueable accepting `List<Id>`/`Set<Id>` without a ≤200 chunk cap risks governor limit exhaustion
- **Batch error recovery (MAJOR)**: If `execute()` sets records to an intermediate status, the `catch` block must revert them to prior status (e.g. `PENDING`) to prevent stuck data
- **Formula field opportunity (MINOR)**: Apex that only derives a value from sibling fields on the same SObject with no cross-object traversal should be replaced with a formula field

### Comment & Formatting Standards (Merge-Safety)
- **BLOCKING**: No comment lines that contain 3 or more consecutive `=` signs (e.g. `// ===`, `// ========`). These are indistinguishable from Git/CI merge conflict separators (`=======`) and corrupt automated conflict resolution. Replace all such dividers with `// -- SECTION NAME --` (double-dash format).
- **BLOCKING**: No comment lines that contain 3 or more consecutive `>` signs (e.g. `// >>>`, `console.log('val>>>')`). These match the `>>>>>>>` merge conflict end marker.
- **BLOCKING**: No comment lines that contain 3 or more consecutive `<` signs. These match the `<<<<<<<` merge conflict start marker.
- **Approved alternatives** for section headers: `// -- SECTION NAME --`; SFDX `// region`/`// endregion`; standard docblock `/** ... */`. Plain `//` for blank separators.
- Scan with: `grep -rn "\/\/.*=\{3,\}\|\/\/.*>\{3,\}\|\/\/.*<\{3,\}" force-app/`

### Documentation & Style
- Class/Test header block required (see format in `references/checklist.md`)
- Method docblocks required for public/global methods
- Naming: Apex `{{APEX_PREFIX}}_`, LWC `{{LWC_PREFIX}}`, subflows `{{APEX_PREFIX}}F_`, screen flows `{{APEX_PREFIX}}SF_`, custom fields `{{APEX_PREFIX}}_`
- API version {{SF_API_VERSION}} on all `.cls-meta.xml` and `.js-meta.xml`

---

## 6. Mode A — Test Classes

Apply the test-specific checks from `references/checklist.md §Mode-A`.

Quick summary:
- `@IsTest` on class and methods
- `@TestSetup` for data; no `SeeAllData=true`
- `{{APEX_PREFIX}}_TestDataFactory` for all test data creation
- Every test has `System.assert*` assertion
- `System.runAs()` for role/permission-based logic
- Positive + negative + bulk + error paths covered
- **Coverage target ≥ {{TARGET_COVERAGE}}%** — report actual coverage figures; raise Major finding if below target, Blocking if below `{{MIN_COVERAGE}}%`

### LWC Jest Tests

Every LWC component in scope must have a `__tests__/<componentName>.test.js` file:

- Use `createElement` from `'lwc'`, wrap each test in `afterEach(() => { document.body.removeChild(el); jest.clearAllMocks(); })`
- Wire adapters mocked via `registerApexTestWireAdapter` / `registerLdsTestWireAdapter` from `@salesforce/wire-service-jest-util`
- Project logger component stubbed under the test mocks directory and mapped in `jest.config.js`
- Run: `npm run test -- --testPathPattern=<componentName>` and report pass/fail counts
- **All Jest tests must pass** — any failure is a Blocking finding
- Cover: initial render, `@api` property setters, wire mock responses (data + error paths), user interactions (`click`, `change`), getters with edge-case inputs (null, empty, boundary values)

---

## 7. Mode B — Regular Files

Apply all checks from `references/checklist.md §Mode-B`. Raise findings at:

| Level | When |
|---|---|
| **Blocking** | Security vulnerabilities, data loss, GDPR, broken functionality |
| **Major** | Performance issues, missing tests, CRUD/FLS violations, architecture debt |
| **Minor** | Style deviations, missing docs, non-critical refactoring |
| **Nit** | Formatting, naming, minor suggestions |

---

## 8. Quality Gates

Run these and include results in the output:

```bash
# Static analysis
sf code-analyzer run \
  --target <file1> --target <fileN> \
  --view detail

# IDOR security scanner
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py \
  --files <space-separated files> --output terminal

# Apex tests (targeted)
sf apex run test --class-names {{APEX_PREFIX}}_MyClassTest --result-format human --wait 10
# OR full local
sf apex run test --test-level RunLocalTests --result-format human --wait 10

# Merge-conflict-unsafe comment check
grep -rn "\/\/.*={3,}\|\/\/.*>{3,}\|\/\/.*<{3,}" force-app/main/default/
```

---

## 9. Output Template

```
---
Scope: [all modified / staged only]
Mode: [Test Classes / Regular / Mixed]
Context: [SAD/FDS sections or "No specific AC referenced"]

### Findings by File

**`<filename>`**
- Issue: <description>
- Risk: <security/performance/maintainability/documentation>
- Rule: <rule name from checklist>
- Fix: <code snippet or action>

### Cross-Cutting Status
- Security & Data Access: pass/warn — <details>
- Performance & Limits: pass/warn — <details>
- Logging & Maintainability: pass/warn — <details>
- Comment merge-safety: pass/warn — <details>
- Documentation & Style: pass/warn — <details>

### Quality Gates
- sf code-analyzer: pass/fail — <violation count, 0 required; list any PMD suppressions in use and whether they have justifying comments>
- IDOR scanner: pass/fail — <critical issues or "None">
- Apex tests: pass/fail — <exact coverage %, ≥{{TARGET_COVERAGE}}% required>
- LWC Jest tests: pass/fail — <pass/fail count, all must pass> (N/A if no LWC in scope)
- Flow validation: pass/warn — <if applicable>
- Merge-conflict-unsafe comments: pass/fail — <count or "None found">

### Coverage vs Work Item AC
- AC implemented: Yes / Partial / No
- Gaps: <list>
---
```

---

## 10. Conventional Commit Message

Format (per https://www.conventionalcommits.org/en/v1.0.0):

```
<type>[optional scope][!]: <description>

[optional body — wrap at ~100 chars]

[optional footer — BREAKING CHANGE: ... or Refs: #12345]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

---

## 11. {{CICD_TOOL}} Commit Instructions

1. Commit through your CI/CD tool's review/commit screen for the work item linked to your sandbox
2. Select the source org and the changed metadata (Source Format enabled)
3. Paste the Conventional Commit message into the commit dialog
4. Submit — your CI/CD tool stages and pushes to the feature branch
5. This skill does **not** perform commits

---

## 12. Tone & Safety

- Professional, concise, no emojis
- No sensitive data in review notes or commit text
- No employee full names — use roles/initials
- No internal URLs — use generic placeholders
- If work item comment creation fails: display error, offer retry or save draft locally
