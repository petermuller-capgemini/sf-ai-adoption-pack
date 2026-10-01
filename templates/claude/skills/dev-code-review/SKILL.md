---
name: dev-code-review
description: Salesforce secure code review assistant. Analyse modified or staged Apex, LWC, Trigger, and Flow files against org standards, SAD/FDS, and Work Item acceptance criteria. Runs static analysis (sf code-analyzer), IDOR scanner, and Apex tests. Produces structured findings, suggested Conventional Commit message, and {{CICD_TOOL}} commit instructions. Two modes: Test Classes (Mode A) vs Regular Files (Mode B) with auto-detection. Use whenever the user asks to review code, check a PR, validate changes before commit, or audit a work item's implementation.
---

# dev-code-review

## Quick Start

1. Load the full review checklist (§13 below)
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

Ask all at once (use `vscode_askQuestions`):

> 1. Review **all modified files** or **only staged files**?
> 2. Any checks to skip this pass (linting, accessibility, tests)?
> 3. Any extra context from SAD/FDS/Work Item (sections, edge cases, limits)?

---

## 4. Cross-Cutting Rules (ALL files)

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
- Class/Test header block required (see format in §13)
- Method docblocks required for public/global methods
- Naming: Apex `{{APEX_PREFIX}}_`, LWC `{{LWC_PREFIX}}`, subflows `{{APEX_PREFIX}}F_`, screen flows `{{APEX_PREFIX}}SF_`, custom fields `{{APEX_PREFIX}}_`
- API version {{SF_API_VERSION}} on all `.cls-meta.xml` and `.js-meta.xml`

---

## 5. Mode A — Test Classes

Quick summary:
- `@IsTest` on class and methods
- `@TestSetup` for data; no `SeeAllData=true`
- `{{APEX_PREFIX}}_TestDataFactory` for all test data creation
- Every test has `System.assert*` assertion
- `System.runAs()` for role/permission-based logic
- Positive + negative + bulk + error paths covered
- **Coverage target ≥ {{TARGET_COVERAGE}}%** — report actual coverage figures; raise Major finding if below target, Blocking if below `{{MIN_COVERAGE}}%`

Full checklist: §13 "Mode A — Test Classes".

### LWC Jest Tests

Every LWC component in scope must have a `__tests__/<componentName>.test.js` file:

- Use `createElement` from `'lwc'`, wrap each test in `afterEach(() => { document.body.removeChild(el); jest.clearAllMocks(); })`
- Wire adapters mocked via `registerApexTestWireAdapter` / `registerLdsTestWireAdapter` from `@salesforce/wire-service-jest-util`
- Project logger component stubbed under the test mocks directory and mapped in `jest.config.js`
- Run: `npm run test -- --testPathPattern=<componentName>` and report pass/fail counts
- **All Jest tests must pass** — any failure is a Blocking finding
- Cover: initial render, `@api` property setters, wire mock responses (data + error paths), user interactions (`click`, `change`), getters with edge-case inputs (null, empty, boundary values)

---

## 6. Mode B — Regular Files

Apply all checks from §13 "Mode B — Regular Files". Raise findings at:

| Level | When |
|---|---|
| **Blocking** | Security vulnerabilities, data loss, GDPR, broken functionality |
| **Major** | Performance issues, missing tests, CRUD/FLS violations, architecture debt |
| **Minor** | Style deviations, missing docs, non-critical refactoring |
| **Nit** | Formatting, naming, minor suggestions |

---

## 7. Quality Gates

Run these and include results in the output:

```bash
# Static analysis
sf code-analyzer run \
  --target <file1> --target <fileN> \
  --view detail

# IDOR security scanner
python3 .claude/skills/salesforce-code-quality/scripts/idor_scanner.py \
  --files <space-separated files> --output terminal

# Apex tests (targeted)
sf apex run test --class-names {{APEX_PREFIX}}_MyClassTest --result-format human --wait 10
# OR full local
sf apex run test --test-level RunLocalTests --result-format human --wait 10

# Merge-conflict-unsafe comment check
grep -rn "\/\/.*={3,}\|\/\/.*>{3,}\|\/\/.*<{3,}" force-app/main/default/
```

---

## 8. Output Template

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

## 9. Conventional Commit Message

Format (per https://www.conventionalcommits.org/en/v1.0.0):

```
<type>[optional scope][!]: <description>

[optional body — wrap at ~100 chars]

[optional footer — BREAKING CHANGE: ... or Refs: #12345]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

---

## 10. {{CICD_TOOL}} Commit Instructions

1. Commit through your CI/CD tool's review/commit screen for the work item linked to your sandbox
2. Select the source org and the changed metadata (Source Format enabled)
3. Paste the Conventional Commit message into the commit dialog
4. Submit — your CI/CD tool stages and pushes to the feature branch
5. This skill does **not** perform commits

---

## 11. Tone & Safety

- Professional, concise, no emojis
- No sensitive data in review notes or commit text
- No employee full names — use roles/initials
- No internal URLs — use generic placeholders
- If work item comment creation fails: display error, offer retry or save draft locally

---

## 12. Agent Protocol

Use `vscode_askQuestions` for any clarification needed mid-task rather than stopping. Delegate heavy analysis (large class scans, bulk metadata queries) to subagents via `runSubagent` and instruct them to return only key findings — no raw data dumps.

---

## 13. Full Checklist Reference

### Mode A — Test Classes

- [ ] `@IsTest` annotation on class and all test methods
- [ ] `@TestSetup` used for shared data; never `SeeAllData=true`
- [ ] `{{APEX_PREFIX}}_TestDataFactory` for all record creation — no ad-hoc `new SObject()` in test bodies
- [ ] Every test method contains at least one `System.assert*` with a descriptive message
- [ ] `System.runAs()` wraps logic that exercises permission/role-based code paths
- [ ] Covers: positive path, negative path, bulk (≥200 records), error/fault path
- [ ] No org data dependency — all data created in `@TestSetup` or test method
- [ ] No external callouts without `Test.startTest/stopTest` + mock
- [ ] No `Test.setMock` omitted for Queueable/Future callout tests
- [ ] Unused test methods, setup logic, or variables removed
- [ ] **Apex test coverage ≥ {{TARGET_COVERAGE}}%** — report exact percentage; below target = Major finding, below `{{MIN_COVERAGE}}%` = Blocking

#### LWC Jest Tests (Mode A for LWC)

- [ ] Every modified LWC component has a `__tests__/<componentName>.test.js`
- [ ] Uses `createElement` + `afterEach` DOM teardown + `jest.clearAllMocks()`
- [ ] Wire adapters stubbed with `registerApexTestWireAdapter` / `registerLdsTestWireAdapter`
- [ ] Project logger component mapped in `jest.config.js`; any new org-scoped import has a corresponding mock
- [ ] **All tests pass** (`npm run test -- --testPathPattern=<name>`) — any failure is Blocking
- [ ] Covers: initial render, `@api` setters, wire data+error paths, user interactions, getter edge cases (null/empty)

### Mode B — Regular Files

#### Apex — Security & IDOR

- [ ] `with sharing`, `without sharing`, or `inherited sharing` declared on every class
- [ ] `without sharing` classes have an inline comment explaining why elevated access is required
- [ ] No dynamic SOQL from user input without `String.escapeSingleQuotes()` or bind variable
- [ ] `WITH USER_MODE` or explicit CRUD/FLS checks on all queries in `with sharing` classes
- [ ] IDOR requery: records accepted by ID are re-queried with `WITH SECURITY_ENFORCED` before DML
- [ ] Methods do not accept `userId` as parameter — use `UserInfo.getUserId()`
- [ ] No DML/SOQL in loops — **includes the transitive case**: if a method that contains SOQL or DML is called from inside a loop, that is the same governor-limit violation even though the SOQL literal does not appear in the loop body. Trace call chains: if the loop body calls `processX(record)` and `processX` issues a query, raise the same **Blocking** finding and recommend bulk-refactoring the callee to accept a collection
- [ ] HTTP callouts validate response status codes and sanitize inputs
- [ ] `@RestResource` / `@AuraEnabled` catch blocks return generic safe response — no `e.getMessage()` to consumer
- [ ] Token expiry validated alongside token value match

#### Apex — Meta-XML

- [ ] `<apiVersion>{{SF_API_VERSION}}</apiVersion>` on every modified `.cls-meta.xml`
- [ ] New custom fields recorded in delta data dictionary with data classification
- [ ] Every custom object and field has `<description>`

#### Apex — Naming & Structure

- [ ] Class name reflects actual domain (no `*AccountConstants` holding order logic)
- [ ] Method visibility minimised: `private` → `protected` → `public` → `global` (justify each escalation)
- [ ] Abstract/override methods declare explicit access modifier
- [ ] Business logic in instance-based classes — not in all-static service/manager/handler
- [ ] `@AuraEnabled`/`@InvocableMethod`/`@RestResource` entry points only validate params and delegate
- [ ] Constants declared `static final UPPER_SNAKE_CASE` with minimized visibility
- [ ] No string/numeric literals in business logic — use constants class or Custom Label
- [ ] `AuraHandledException` messages are Custom Labels (`System.Label.X`), not hardcoded strings — even input-validation guards are potentially customer-facing via LWC error toasts

#### Apex — Static Analysis (sf code-analyzer)

- [ ] **Zero violations** from `sf code-analyzer run --target <file> --view detail`
- [ ] `@SuppressWarnings('PMD.<RuleName>')` used **only as a last resort** when:
  - The violation is a confirmed false positive, AND
  - Fixing it would require a non-functional structural change
- [ ] Every `@SuppressWarnings` has an inline justifying comment on the line immediately above:
  ```apex
  // PMD suppress: <RuleName> — <reason why this is a false positive or why it cannot be fixed>
  @SuppressWarnings('PMD.<RuleName>')
  ```
- [ ] Security-category PMD violations (e.g. `ApexCRUDViolation`, `ApexSharingViolations`) are **never** suppressed — fix them

#### Apex — Comment Merge-Safety ← **CI/CD CRITICAL**

- [ ] No `// ===...` (3+ consecutive `=` in a comment line) — replace with `// -- SECTION --`
- [ ] No `// >>>...` (3+ consecutive `>` in a comment or log string)
- [ ] No `// <<<...` (3+ consecutive `<` in a comment)
- [ ] Approved divider formats: `// -- SECTION NAME --`, `// region`, `/** ... */`, bare `//`
- [ ] Scan: `grep -rn "\/\/.*={3,}\|\/\/.*>{3,}\|\/\/.*<{3,}" force-app/`

#### Apex — Logging

- [ ] `{{LOGGER_CLASS}}` via `{{LOGGER_FACTORY}}.getFactory().createLogger('<ClassName>')` — no `System.debug()`
- [ ] No PII (email, external identity ID, customer identifier) in log calls — mask with a data masking utility
- [ ] At most 1–2 `LOGGER.info` on a single execution path; trace points use `LOGGER.debug`
- [ ] Error paths include key variable context (IDs, method name, input values)
- [ ] `logger.publishBatchedLogEvents()` called in `finally` for batched loggers

#### Apex — Performance

- [ ] No duplicate SOQL for same record in one transaction
- [ ] `Schema.getDescribe()` not in hot paths — cached as `static final`
- [ ] `containsKey(key)` + `get(key)` anti-pattern replaced with single `get` + null check
- [ ] Business filter conditions pushed into SOQL `WHERE` rather than in-memory filtering on indexable fields
- [ ] `FeatureManagement.checkPermission()` routed through a permission cache utility

#### Apex — Configuration

- [ ] No hardcoded field lists — use `Schema.FieldSet` or Custom Metadata Types
- [ ] Query builder logic encapsulated in builder class
- [ ] Cron expressions and schedule interval values not hardcoded as string literals — use Custom Metadata so schedule changes do not require a code deployment

#### Apex — Security — Custom Permissions

- [ ] `@AuraEnabled` methods that gate a destructive or privileged action must verify the required custom permission server-side via `FeatureManagement.checkPermission('<PermApiName>')` — client-side-only checks (`hasCustomPermission` in LWC) are bypassable and a **BLOCKING** finding (OWASP A01)
- [ ] Permission-set names referenced as string literals in Apex (test or production) must be constants, either in a central constants class or in `{{APEX_PREFIX}}_TestDataFactory` for test helpers — inline strings are a MINOR finding (cross-class duplication) and become a MAJOR finding if the same literal appears in 3 or more classes

#### Apex — Async Apex (Batch & Queueable)

- [ ] **Batch duplicate-run guard** — A `Database.Batchable` or `Schedulable` class that processes shared records must guard against concurrent execution by querying `AsyncApexJob` for an already-running instance of the same class before enqueuing a new one. Missing guard on records that can be picked up twice is a **MAJOR** finding. Guard query pattern: `[SELECT Id FROM AsyncApexJob WHERE ApexClass.Name = 'ClassName' AND Status NOT IN ('Aborted', 'Completed', 'Failed') LIMIT 1]`
- [ ] **Duplicate-run check placement** — The concurrent-execution guard must live inside `execute(SchedulableContext ctx)`, not in the class constructor. Constructors cannot reliably query job status at the correct moment. Misplaced check is a **MAJOR** finding.
- [ ] **Self-chaining batch anti-pattern** — A `finish()` method that calls `Database.executeBatch(this)` or `Database.executeBatch(new SameBatchClass(...))` when a `Schedulable` already covers re-execution is redundant and risks double-processing in-flight records. Raise a **MAJOR** finding and recommend removing the self-chain.
- [ ] **Queueable input list size cap** — A `Queueable` accepting a `List<Id>` or `Set<Id>` in its constructor must cap the chunk size to avoid governor limit exhaustion (default safe cap: 200). Missing size guard with no chunking strategy is a **MAJOR** finding.
- [ ] **Batch execute() status rollback on exception** — When `execute()` sets records to an intermediate status (e.g. `IN_PROGRESS`) before processing, a `catch` block that only logs the exception without reverting those records to their previous status (e.g. `PENDING`) leaves data stuck. Missing status rollback in the batch `catch` block is a **MAJOR** finding.
- [ ] **Batch size from Custom Metadata** — A hardcoded `Database.executeBatch(batch, 200)` batch size is a MINOR finding; batch size must be read from Custom Metadata so it can be tuned without a deployment.
- [ ] **Formula field opportunity** — When Apex computes a derived boolean or scalar value solely from other fields on the same SObject (no cross-object traversal, no Apex logic), flag as a **MINOR** suggestion to replace with a Salesforce formula field and remove the Apex logic.

#### Apex — Testing (coverage)

- [ ] Test data centralised in `{{APEX_PREFIX}}_TestDataFactory`
- [ ] `System.runAs()` with correct persona permission set group
- [ ] All AC-mandatory fields individually validated at controller layer

#### LWC

- [ ] One-directional data flow: parent → child via `@api`; child → parent via `CustomEvent`
- [ ] No in-place mutation of an `@api`-received object — shallow copy before mutation
- [ ] `event.detail` uses primitive types only
- [ ] `composed: true` only when cross-shadow boundary communication is documented
- [ ] `refreshApex()` used for Apex wire results; `notifyRecordUpdateAvailable()` for LDS wire
- [ ] Apex and LDS not mixed for same SObject record unless justified
- [ ] Data access priority: LDS base components → GraphQL → LDS wire → Apex
- [ ] Custom Metadata Types accessed via Apex (LDS adapters do not support `__mdt`)
- [ ] No `console.log`/`console.debug` in production code — use the project logger component
- [ ] No debug strings with `>>>`, `<<<`, `===` in console output or comments
- [ ] `<apiVersion>{{SF_API_VERSION}}</apiVersion>` in `.js-meta.xml`
- [ ] `@track` only for nested object/array mutation — not for primitives
- [ ] SLDS utility classes use `slds-var-` prefix tokens; no deprecated bare pixel values

#### Flows

- [ ] One active Before-Save and one active After-Save per object
- [ ] Before-Save: same-record updates only (no DML/callouts)
- [ ] After-Save: DML on related records, callouts, or new record creation
- [ ] No Get/Update/Create/Delete Records inside a LOOP — accumulate in collection first
- [ ] `$Record__Prior` + `ISCHANGED(...)` logic to prevent recursion
- [ ] **Every** CRUD/Action/Subflow element has a fault path
- [ ] All fault paths route to a shared fault-handling subflow (not inline)
- [ ] Fault paths pass: Flow API Name, Element Name, Record ID, `{!$Flow.FaultMessage}`
- [ ] Screen Flows: fault paths display user-friendly error screen
- [ ] Declarative Flow Tests exist (positive, negative, each Decision branch, fault path)
- [ ] Apex test classes exercise the Flow via DML with ≥{{TARGET_COVERAGE}}% coverage and assertions

### Class Header Block Format

```apex
/**
 * @description       : <What this class does>
 * @author            : <Author Name>
 * @last modified on  : <Date>
 * @last modified by  : <Author Name>
 * Modifications Log
 * Ver   Date         Author       Modification
 * 1.0   DD-MM-YYYY   Name         Initial Version
 **/
```

### Method Docblock Format

```apex
/**
 * @description
 * @param <Type> <paramName>
 * @return <Type>
 **/
```
