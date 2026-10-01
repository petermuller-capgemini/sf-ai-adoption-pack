---
name: flow-standards
description: "Apply {{PROJECT_NAME}} Salesforce Flow coding standards — naming, security, bulkification, fault paths, testing, and deployment checklist. Run with: /flow-standards [FlowName]"
---

# flow-standards

Apply the full {{PROJECT_NAME}} Flow development standards.

**Applies to:** `force-app/**/flows/**`

---

## 1. High-Level Principles

- **Flows are first-class assets**: treat with the same rigor as Apex, LWC, and other metadata.
- **Self-documenting**: descriptions, comments, and naming conventions.
- **Security by design**: enforce least privilege, data access controls, avoid exposing sensitive information.
- **No hardcoding**: never hardcode IDs, URLs, or sensitive values — use Custom Metadata, Custom Settings, or Labels.
- **Peer review required** before deployment.
- **Version control**: all Flows must be source-tracked with meaningful commit messages referencing work items.

---

## 2. Naming Conventions

- **Flow API Name**: `{{FLOW_PREFIX}}_<Object/Process>_<Type>_<Purpose>` (e.g., `{{FLOW_PREFIX}}_Opportunity_AfterSave_UpdateStage`)
- **Subflows**: `{{SUBFLOW_PREFIX}}_<Purpose>` (e.g., `{{SUBFLOW_PREFIX}}_HandleFault`)
- **Variables**: `v_` single variables, `col_` collections, `f_` formulas, `c_` constants
- **Elements**: Prefix by type (e.g., `GET_Account_ById`, `DEC_IsActive`, `ASSIGN_SetDefaults`, `LOOP_Contacts`, `SUBF_LogError`)
- No abbreviations unless team-standard and documented.
- Every Flow, element, and variable must have a meaningful description in English.

---

## 3. Security & Data Access

- **Run Flows in User Context** unless documented business need for System Context exists. If System Context is used, document justification and gate privileged actions with Custom Permissions.
- **Respect CRUD/FLS**: Flows do not enforce CRUD/FLS automatically. For record-triggered Flows, check user permissions before updating/creating records. For System Context Flows, simulate FLS using Apex actions or subflows.
- **No hardcoded IDs or sensitive data** in Flows, screens, or fault messages.
- **Screen Flows**: never display technical errors or sensitive data to users; use user-friendly error messages and log details securely.
- **Enforce server-side security for Invocable Apex**: Any Invocable or `@AuraEnabled` Apex called by Flows must re-query inputs (IDs) using `WITH SECURITY_ENFORCED`. Never accept `userId` from the Flow — use server-side `UserInfo.getUserId()`.
- **Structured logging**: use `{{LOGGER_CLASS}}` for Flow-invoked Apex actions and centralized fault handling subflows.
- **IDOR scanning**: run `idor_scanner.py` on Invocable Apex classes referenced by Flows.
- **Naming & prefix**: use the project flow prefix where applicable (e.g., `{{FLOW_PREFIX}}_...`).

---

## 4. Design & Performance

- **One Flow per object per context**: only one active before-save and one after-save record-triggered Flow per object.
- **Bulkification**: never place Get/Create/Update/Delete elements inside Loops. Accumulate records in collections; perform DML outside the loop.
- **Before-Save optimization**: use Assignment elements to update `$Record` fields directly. Never use Update Records in before-save context — it's redundant DML.
- **After-Save field updates on same object**: if only updating the triggering record's fields, use before-save context with Assignment, not after-save with Update Records.
- **Governor limit violations roll back the ENTIRE transaction — fault paths do NOT prevent this**: design flows to stay well within limits. Use before-save context to minimize DML count; collapse multiple record updates into single collections; avoid patterns where a large batch each triggers additional SOQL or DML inside a loop.
- **Remove redundant elements**: delete Get Records elements whose outputs are never referenced. Same for unused Loops, Assignments, or Decision outcomes.
- **Unused resources**: delete unused variables, formulas, and constants. Use Find Unused Resources in Flow Builder.
- **Element naming**: never use auto-generated names (e.g., `Outcome_1_of_Decision_1`). Use descriptive labels.
- **Reusable logic**: use Subflows for shared logic; accept/return collections.
- **No recursion**: use entry conditions and ISCHANGED patterns.
- **Scheduled actions**: use Scheduled Paths for time-based logic, not Pause elements.
- **No unnecessary queries**: only fetch fields and records needed.
- **Cache lookups**: reuse Get Records results via variables.

---

## 5. Logging & Exception Handling

### Structured Logging

- Use a structured "Log Message" Apex action for consistent, structured logging from flows.
- Avoid batched logging in flows unless explicitly needed for high-volume scenarios.
- Exception objects should be passed to `ERROR`/`FATAL` in underlying Apex; don't concatenate exception messages (loses stack traces).

### Fault Paths (Mandatory)

Every Flow containing DML (Create, Get, Update, Delete Records), Action, or Subflow elements **must** include fault paths.

**Fault path requirements:**

1. Add a fault path to every eligible element.
2. Route all fault paths to the centralized `{{SUBFLOW_PREFIX}}_HandleFault` subflow.
3. Pass contextual variables: Flow API name, element name, record ID, and `{!$Flow.FaultMessage}`.
4. **Screen Flows**: display a user-friendly error screen using `{!$Flow.FaultMessage}`. Never show raw stack traces to end users.
5. **Record-Triggered Flows**: route fault paths to subflow which creates an Error Log record and optionally sends admin notification.

**Transaction rollback caution**: adding a fault path means the transaction does **not** automatically roll back on error. Prior DML remains committed. Add a Custom Error element at the end of the fault path if rollback is needed.

### `{{SUBFLOW_PREFIX}}_HandleFault` subflow pattern

```
Subflow Input Variables:
  v_FlowApiName   → Text, Input, Required
  v_ElementName   → Text, Input, Required
  v_RecordId      → Text, Input, Optional
  v_FaultMessage  → Text, Input, Required

Actions:
  1. CREATE → Error_Log__c (Automation_Name__c, Error__c, recordId__c)
  2. LOG    → {{LOGGER_CLASS}} Log Message (FATAL, v_FlowApiName + ': ' + v_FaultMessage)
  3. EMAIL  → (Optional) Send notification to admin distribution list
```

---

## 6. Documentation

Flow Description field template:

```
Name            : {{FLOW_PREFIX}}_<Object/Process>_<Type>_<Purpose>
Owner           : <Team/Owner>
Run Context     : <User|System> (document why if System)
Entry Criteria  : <Concise summary>
Purpose         : <Business outcome>
Key Decisions   : <Major branches>
Data Touches    : <Objects/Fields read/write>
Error Handling  : <How faults are handled>
Dependencies    : <Subflows, Invocable Apex, External Services>
Change Log
Ver   Date        Author        Change
1.0   DD-MM-YYYY  <Name>        Initial version
```

Every element that performs business logic or I/O must have a description.

---

## 7. Testing & Validation

### Flow Tests (Record-Triggered Flows)

Required scenarios per Flow:

| Scenario | Required |
|---|---|
| Positive/happy path | Yes |
| Negative path (does not meet entry criteria) | Yes |
| Each Decision branch | Yes |
| Bulk scenario (≥200 records) | Yes |
| Fault path trigger | Yes |
| ISCHANGED guard | Recommended |

**How to create Flow Tests:**
1. Open Flow → click Debug → Run
2. On success, click "Convert to Test" → name descriptively
3. To run all: Flow Builder → View Tests → Run All

### Apex Tests for Flows

```apex
@isTest
private class {{FLOW_PREFIX}}_AccountAfterSave_Test {
    @TestSetup
    static void setup() {
        Account testAccount = {{TEST_DATA_FACTORY}}.createAccount('Test Corp', false);
        insert testAccount;
    }

    @isTest
    static void testHappyPath_StageUpdated() {
        Account acc = [SELECT Id, Industry, {{APEX_PREFIX}}_Status__c FROM Account LIMIT 1];
        Test.startTest();
        acc.Industry = 'Healthcare';
        update acc;
        Test.stopTest();

        Account result = [SELECT {{APEX_PREFIX}}_Status__c FROM Account WHERE Id = :acc.Id];
        System.assertEquals('Reviewed', result.{{APEX_PREFIX}}_Status__c, 'Flow should set status to Reviewed when Industry changes');
    }
}
```

**Apex test requirements:**
- Use `@TestSetup` and `{{TEST_DATA_FACTORY}}`; never `seeAllData=true`
- Wrap trigger-firing DML in `Test.startTest()` / `Test.stopTest()`
- Assert on Flow outcomes (field values, related records, Error_Log__c entries)
- Cover positive, negative, bulk (≥200), and fault path scenarios
- Target ≥{{TARGET_COVERAGE}}% coverage on any Invocable Apex called by the Flow
- Include `System.runAs()` tests for User Context behavior

---

## 8. Deployment & Change Management

- **API Version**: always set `<apiVersion>{{SF_API_VERSION}}</apiVersion>` in every `.flow-meta.xml`. Never use a version more than two releases behind the org's current release.
- **Deployment**: use `sf project deploy validate` before activating Flows.
- **Post-deploy**: confirm only one active before-save and one after-save Flow per object. Review Flow Trigger Explorer.

---

## Pre-Commit Checklist

- [ ] Flow Description header present and current
- [ ] API Name and element/resource naming conventions followed
- [ ] User vs System context explicitly set and documented
- [ ] Entry conditions precise; ISCHANGED patterns used
- [ ] No DML/Get inside loops; collections used correctly
- [ ] Governor limits respected — verify loop/collection patterns cannot exhaust limits in bulk (≥200 record) scenarios
- [ ] **Fault paths on ALL CRUD, Action, and Subflow elements** — routed to `{{SUBFLOW_PREFIX}}_HandleFault`
- [ ] Screen Flows: fault paths show user-friendly error screen
- [ ] Record-Triggered Flows: fault paths log to Error_Log__c via subflow
- [ ] Transaction rollback: Custom Error added at end of fault path if rollback is needed
- [ ] Logging subflow used
- [ ] Subflows used for reusable logic; accept/return collections
- [ ] **Flow Tests** created for each decision branch (positive + negative + fault)
- [ ] **Apex Tests** cover bulk (≥200), fault path, and `System.runAs()` scenarios
- [ ] No sensitive data in user-visible messages

---

## Quality Gates

```bash
# Flow static analysis
sf code-analyzer run --target force-app/main/default/flows/{{FLOW_PREFIX}}_MyFlow.flow-meta.xml --view detail

# Invocable Apex IDOR scan
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py --files force-app/main/default/classes/{{APEX_PREFIX}}_FlowHelper.cls --output terminal

# Apex tests
sf apex run test --class-names {{APEX_PREFIX}}_FlowHelperTest --result-format human --code-coverage --wait 10

# Deployment validation
sf project deploy validate --source-dir force-app/main/default/flows --test-level RunLocalTests
```
