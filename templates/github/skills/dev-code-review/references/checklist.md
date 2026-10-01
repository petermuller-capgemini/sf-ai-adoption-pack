# Dev Code Review Checklist Reference

## Mode A — Test Classes

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

### LWC Jest Tests (Mode A for LWC)

- [ ] Every modified LWC component has a `__tests__/<componentName>.test.js`
- [ ] Uses `createElement` + `afterEach` DOM teardown + `jest.clearAllMocks()`
- [ ] Wire adapters stubbed with `registerApexTestWireAdapter` / `registerLdsTestWireAdapter`
- [ ] Project logger component mapped in `jest.config.js`; any new org-scoped import has a corresponding mock
- [ ] **All tests pass** (`npm run test -- --testPathPattern=<name>`) — any failure is Blocking
- [ ] Covers: initial render, `@api` setters, wire data+error paths, user interactions, getter edge cases (null/empty)

---

## Mode B — Regular Files

### Apex

#### Security & IDOR

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

#### Meta-XML

- [ ] `<apiVersion>{{SF_API_VERSION}}</apiVersion>` on every modified `.cls-meta.xml`
- [ ] New custom fields recorded in delta data dictionary with data classification
- [ ] Every custom object and field has `<description>`

#### Naming & Structure

- [ ] Class name reflects actual domain (no `*AccountConstants` holding order logic)
- [ ] Method visibility minimised: `private` → `protected` → `public` → `global` (justify each escalation)
- [ ] Abstract/override methods declare explicit access modifier
- [ ] Business logic in instance-based classes — not in all-static service/manager/handler
- [ ] `@AuraEnabled`/`@InvocableMethod`/`@RestResource` entry points only validate params and delegate
- [ ] Constants declared `static final UPPER_SNAKE_CASE` with minimized visibility
- [ ] No string/numeric literals in business logic — use constants class or Custom Label
- [ ] `AuraHandledException` messages are Custom Labels (`System.Label.X`), not hardcoded strings — even input-validation guards are potentially customer-facing via LWC error toasts

#### Static Analysis (sf code-analyzer)

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

#### Comment Merge-Safety ← **CI/CD CRITICAL**

- [ ] No `// ===...` (3+ consecutive `=` in a comment line) — replace with `// -- SECTION --`
- [ ] No `// >>>...` (3+ consecutive `>` in a comment or log string)
- [ ] No `// <<<...` (3+ consecutive `<` in a comment)
- [ ] Approved divider formats: `// -- SECTION NAME --`, `// region`, `/** ... */`, bare `//`
- [ ] Scan: `grep -rn "\/\/.*={3,}\|\/\/.*>{3,}\|\/\/.*<{3,}" force-app/`

#### Logging

- [ ] `{{LOGGER_CLASS}}` via `{{LOGGER_FACTORY}}.getFactory().createLogger('<ClassName>')` — no `System.debug()`
- [ ] No PII (email, external identity ID, customer identifier) in log calls — mask with a data masking utility
- [ ] At most 1–2 `LOGGER.info` on a single execution path; trace points use `LOGGER.debug`
- [ ] Error paths include key variable context (IDs, method name, input values)
- [ ] `logger.publishBatchedLogEvents()` called in `finally` for batched loggers

#### Performance

- [ ] No duplicate SOQL for same record in one transaction
- [ ] `Schema.getDescribe()` not in hot paths — cached as `static final`
- [ ] `containsKey(key)` + `get(key)` anti-pattern replaced with single `get` + null check
- [ ] Business filter conditions pushed into SOQL `WHERE` rather than in-memory filtering on indexable fields
- [ ] `FeatureManagement.checkPermission()` routed through a permission cache utility

#### Configuration

- [ ] No hardcoded field lists — use `Schema.FieldSet` or Custom Metadata Types
- [ ] Query builder logic encapsulated in builder class
- [ ] Cron expressions and schedule interval values not hardcoded as string literals — use Custom Metadata so schedule changes do not require a code deployment

#### Security — Custom Permissions

- [ ] `@AuraEnabled` methods that gate a destructive or privileged action must verify the required custom permission server-side via `FeatureManagement.checkPermission('<PermApiName>')` — client-side-only checks (`hasCustomPermission` in LWC) are bypassable and a **BLOCKING** finding (OWASP A01)
- [ ] Permission-set names referenced as string literals in Apex (test or production) must be constants, either in a central constants class or in `{{APEX_PREFIX}}_TestDataFactory` for test helpers — inline strings are a MINOR finding (cross-class duplication) and become a MAJOR finding if the same literal appears in 3 or more classes

#### Async Apex (Batch & Queueable)

- [ ] **Batch duplicate-run guard** — A `Database.Batchable` or `Schedulable` class that processes shared records must guard against concurrent execution by querying `AsyncApexJob` for an already-running instance of the same class before enqueuing a new one. Missing guard on records that can be picked up twice is a **MAJOR** finding. Guard query pattern: `[SELECT Id FROM AsyncApexJob WHERE ApexClass.Name = 'ClassName' AND Status NOT IN ('Aborted', 'Completed', 'Failed') LIMIT 1]`
- [ ] **Duplicate-run check placement** — The concurrent-execution guard must live inside `execute(SchedulableContext ctx)`, not in the class constructor. Constructors cannot reliably query job status at the correct moment. Misplaced check is a **MAJOR** finding.
- [ ] **Self-chaining batch anti-pattern** — A `finish()` method that calls `Database.executeBatch(this)` or `Database.executeBatch(new SameBatchClass(...))` when a `Schedulable` already covers re-execution is redundant and risks double-processing in-flight records. Raise a **MAJOR** finding and recommend removing the self-chain.
- [ ] **Queueable input list size cap** — A `Queueable` accepting a `List<Id>` or `Set<Id>` in its constructor must cap the chunk size to avoid governor limit exhaustion (default safe cap: 200). Missing size guard with no chunking strategy is a **MAJOR** finding.
- [ ] **Batch execute() status rollback on exception** — When `execute()` sets records to an intermediate status (e.g. `IN_PROGRESS`) before processing, a `catch` block that only logs the exception without reverting those records to their previous status (e.g. `PENDING`) leaves data stuck. Missing status rollback in the batch `catch` block is a **MAJOR** finding.
- [ ] **Batch size from Custom Metadata** — A hardcoded `Database.executeBatch(batch, 200)` batch size is a MINOR finding; batch size must be read from Custom Metadata so it can be tuned without a deployment.
- [ ] **Formula field opportunity** — When Apex computes a derived boolean or scalar value solely from other fields on the same SObject (no cross-object traversal, no Apex logic), flag as a **MINOR** suggestion to replace with a Salesforce formula field and remove the Apex logic.

#### Testing (coverage)

- [ ] Test data centralised in `{{APEX_PREFIX}}_TestDataFactory`
- [ ] `System.runAs()` with correct persona permission set group
- [ ] All AC-mandatory fields individually validated at controller layer

---

### LWC

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

---

### Flows

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

---

## Class Header Block Format

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

## Method Docblock Format

```apex
/**
 * @description
 * @param <Type> <paramName>
 * @return <Type>
 **/
```
