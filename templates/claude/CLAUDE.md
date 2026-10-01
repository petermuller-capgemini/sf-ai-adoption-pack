# {{PROJECT_NAME}} — Agent Instructions

These rules apply to all AI agents working in this repository ({{PROJECT_DESCRIPTION}}).
Maintained by {{TEAM_NAME}}. Read them before making any changes.

---

## 1. Git and deployment workflow

Before deploying any file to a sandbox or scratch org, retrieve the current org version and diff it:

```bash
sf project retrieve start --metadata "ApexClass:<ClassName>" --target-org <alias>
git diff force-app/main/default/classes/<ClassName>.cls
```

If the diff shows changes you did not make, the local file is stale — merge the org changes before continuing.

Deployment flow: `retrieve from org → diff → fix divergence → deploy → run tests → commit via {{CICD_TOOL}}`.

Do not run destructive git operations (`git reset --hard`, `git push --force`, history rewrites) without explicit confirmation.

---

## 2. Apex test class structure

Every test class should follow a persona-based pattern:

- Use `{{TEST_DATA_FACTORY}}.UserCreator(<persona>, 'LastName')` in `@TestSetup`. Never hardcode a profile name like `'System Administrator'`.
- Wrap every `@IsTest` method body in `System.runAs(testUser)`.
- All SOQL inside `System.runAs` blocks must include `WITH USER_MODE`.
- Coverage target: ≥ {{TARGET_COVERAGE}}% per class, minimum {{MIN_COVERAGE}}% to deploy, 100% of tests passing before promoting.

```apex
@TestSetup
static void setupData() {
    User testUser = new {{TEST_DATA_FACTORY}}.UserCreator('standardUser', 'TestUser').create();
}

@IsTest
static void should_Handle_HappyPath() {
    User testUser = [SELECT Id FROM User WHERE LastName = 'TestUser' LIMIT 1];
    System.runAs(testUser) {
        Test.startTest();
        // exercise code under the persona's real permissions
        Test.stopTest();
        System.assertEquals(expected, actual, 'Descriptive assertion message');
    }
}
```

---

## 3. Apex class header

Every new or modified Apex class needs this header, with version incremented for every substantive change:

```apex
/**
 * @description       : <What this class does — one sentence>
 * @author            : <Full Name>
 * @last modified on  : DD-MM-YYYY
 * @last modified by  : <Full Name>
 * Modifications Log
 * Ver   Date         Author       Modification
 * 1.0   DD-MM-YYYY   <Full Name>  Initial Version
 **/
```

---

## 4. Suppress warnings and lint ignores

Never add a file-level or class-level suppression as a first resort:

1. **Fix the defect.** Refactor so the warning no longer applies.
2. **If the pattern is intentional**, add the narrowest possible local suppression with a comment explaining why.

```apex
// Suppressed: DML runs in SYSTEM_MODE by explicit ExecutionContext contract
@SuppressWarnings('PMD.ApexCRUDViolation')
private void persistResults(List<SObject> records) { ... }
```

```js
// eslint-disable-next-line @lwc/lwc/no-api-reassignments -- intentionally mutated by parent composition pattern
this.value = newValue;
```

---

## 5. No magic literals — use named constants

Never embed raw string or number values inline where a named constant exists or should exist.

- Apex: use a project constants class (e.g. `{{CONFIG_PREFIX}}_Constants`) for status values, error codes, and integration keys. Runtime-configurable values (timeouts, feature flags) belong in Custom Metadata, not inline literals.
- LWC: define constants in a co-located `constants.js` and import from there; use `@salesforce/label` for user-visible text.
- Tests: declare test-only sentinel values as `private static final` constants at the top of the test class.

Before writing helper logic, check whether `{{TEST_DATA_FACTORY}}` or an existing shared utility component already covers the need — never duplicate it.

---

## 6. Logging

Use `{{LOGGER_CLASS}}` via `{{LOGGER_FACTORY}}`. Never log PII or secrets. Mask identifiers before logging:

```apex
private static final {{LOGGER_CLASS}} LOGGER = {{LOGGER_FACTORY}}.getFactory().createLogger('MyClass');
LOGGER.info('Processing order for account: {0}', new Object[]{ maskedAccountId });
```

---

## Agent Protocol

Use `vscode_askQuestions` for any clarification needed mid-task rather than stopping. Delegate heavy analysis (large class scans, bulk org queries) to subagents and instruct them to return only key findings.
