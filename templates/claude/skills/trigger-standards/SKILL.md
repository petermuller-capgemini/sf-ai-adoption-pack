---
name: trigger-standards
description: "Apply {{PROJECT_NAME}} Apex Trigger standards — one trigger per object, thin trigger + handler pattern, bypass toggle, no SOQL/DML in loops, and quality gates. Run with: /trigger-standards [TriggerFile.cls]"
---

# trigger-standards

Apply {{PROJECT_NAME}} Apex Trigger development standards.

**Applies to:** `force-app/**/triggers/**, force-app/**/*TriggerHandler*.cls, force-app/**/*_TriggerHandler*.cls`

---

## Core Rules

### 1. One Trigger Per Object

Only one Apex trigger per SObject. Multiple triggers on the same object lead to unpredictable execution order.

```apex
// ✅ CORRECT: One trigger per object
trigger OrderTrigger on Order__c (before insert, before update, before delete, after insert, after update, after delete, after undelete) {
    new {{APEX_PREFIX}}_OrderTriggerHandler().run();
}

// ❌ WRONG: Two triggers on the same object
trigger OrderAfterTrigger on Order__c (after insert, after update) { ... }
trigger OrderBeforeTrigger on Order__c (before insert) { ... }
```

### 2. Thin Trigger — No Business Logic

Triggers must contain zero business logic. The trigger body must only instantiate and call the handler.

```apex
// ✅ CORRECT: Thin trigger
trigger AccountTrigger on Account (before insert, before update, before delete,
        after insert, after update, after delete, after undelete) {
    new {{APEX_PREFIX}}_AccountTriggerHandler().run();
}

// ❌ WRONG: Business logic in trigger
trigger AccountTrigger on Account (before insert) {
    for (Account acc : Trigger.new) {
        if (String.isBlank(acc.Industry)) {
            acc.addError('Industry is required');  // ❌ Logic in trigger body
        }
    }
}
```

### 3. Trigger Handler Pattern

All business logic lives in a handler class. Use `fflib_SObjectDomain` as the base where applicable, or implement a custom handler interface.

```apex
public class {{APEX_PREFIX}}_AccountTriggerHandler extends fflib_SObjectDomain {

    public {{APEX_PREFIX}}_AccountTriggerHandler(List<Account> records) {
        super(records, Account.SObjectType);
    }

    public class Constructor implements fflib_SObjectDomain.IConstructable {
        public fflib_SObjectDomain construct(List<SObject> sObjectList) {
            return new {{APEX_PREFIX}}_AccountTriggerHandler(sObjectList);
        }
    }

    // Context methods: override only what you need
    @Override
    public void onBeforeInsert() { validateIndustry(); }

    @Override
    public void onAfterInsert() { createWelcomeTask(); }

    @Override
    public void onBeforeUpdate(Map<Id, SObject> existingRecords) {
        handleStatusChange((Map<Id, Account>) existingRecords);
    }

    private void validateIndustry() {
        for (Account acc : (List<Account>) getRecords()) {
            if (String.isBlank(acc.Industry)) {
                acc.addError({{APEX_PREFIX}}_AccountConstants.ERROR_INDUSTRY_REQUIRED);
            }
        }
    }
}
```

### 4. Bypass Toggle via Custom Settings / Custom Metadata

Every trigger handler must support runtime bypass for data migration and integration scenarios.

```apex
// ✅ CORRECT: Check bypass flag before processing
public void onBeforeInsert() {
    if ({{APEX_PREFIX}}_TriggerBypass__c.getInstance().Bypass_AccountTrigger__c) {
        return;
    }
    validateIndustry();
}

// ✅ ALTERNATIVE: Custom Metadata-based bypass
public void onBeforeInsert() {
    if ({{APEX_PREFIX}}_TriggerSettings__mdt.getInstance('AccountTrigger')?.Is_Bypassed__c == true) {
        return;
    }
    validateIndustry();
}
```

### 5. No SOQL in Loops

Never query inside a `for` loop. Bulk-query before the loop and use Maps for lookup.

```apex
// ❌ VIOLATION: SOQL in loop
for (Order__c order : (List<Order__c>) getRecords()) {
    Account acc = [SELECT Id, Name FROM Account WHERE Id = :order.AccountId];  // ❌
}

// ✅ CORRECT: Bulk query + Map
Set<Id> accountIds = new Set<Id>();
for (Order__c order : (List<Order__c>) getRecords()) {
    accountIds.add(order.AccountId);
}
Map<Id, Account> accountsById = new Map<Id, Account>(
    [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
);
for (Order__c order : (List<Order__c>) getRecords()) {
    Account acc = accountsById.get(order.AccountId);
    // process...
}
```

### 6. No DML in Loops

Never perform DML inside a `for` loop. Collect records and DML once — use Unit of Work.

```apex
// ❌ VIOLATION: DML in loop
for (Order__c order : (List<Order__c>) getRecords()) {
    insert new Task(WhatId = order.Id, Subject = 'Follow Up');  // ❌
}

// ✅ CORRECT: Collect then single DML
List<Task> tasksToInsert = new List<Task>();
for (Order__c order : (List<Order__c>) getRecords()) {
    tasksToInsert.add(new Task(WhatId = order.Id, Subject = 'Follow Up'));
}
insert tasksToInsert;

// ✅ BETTER: Unit of Work
fflib_SObjectUnitOfWork uow = Application.UnitOfWork.newInstance();
for (Order__c order : (List<Order__c>) getRecords()) {
    uow.registerNew(new Task(WhatId = order.Id, Subject = 'Follow Up'));
}
uow.commitWork();
```

---

## Handler Class Standards

### Naming Convention

```
{{APEX_PREFIX}}_<ObjectName>TriggerHandler.cls
{{APEX_PREFIX}}_<ObjectName>TriggerHandler_Test.cls
```

**Examples:**
- `{{APEX_PREFIX}}_OrderTriggerHandler.cls`
- `{{APEX_PREFIX}}_AccountTriggerHandler.cls`

### Logging

Use `{{LOGGER_CLASS}}` — never `System.debug()`:

```apex
private static final {{LOGGER_CLASS}} LOGGER =
    {{LOGGER_FACTORY}}.getFactory().createBatchedLogger('{{APEX_PREFIX}}_OrderTriggerHandler');

public void onBeforeInsert() {
    LOGGER.debug('onBeforeInsert: processing {0} records', new List<Object>{ getRecords().size() });
    validateOrders();
}
```

Call `LOGGER.publishBatchedLogEvents()` in `finally` blocks when using batched loggers.

### Context-Specific Methods

Only override context methods that are actually used. Do not create empty overrides.

```apex
// ❌ UNNECESSARY: Empty override
@Override
public void onBeforeUpdate(Map<Id, SObject> existingRecords) {
    // nothing to do
}

// ✅ CORRECT: Only override non-empty methods
```

---

## Recursive Prevention

For operations that may re-fire the same trigger:

```apex
public class {{APEX_PREFIX}}_OrderTriggerHandler extends fflib_SObjectDomain {

    private static Boolean isRunning = false;

    public void onAfterUpdate(Map<Id, SObject> existingRecords) {
        if (isRunning) { return; }
        isRunning = true;
        try {
            processOrderUpdates((Map<Id, Order__c>) existingRecords);
        } finally {
            isRunning = false;
        }
    }
}
```

---

## Test Standards

```apex
@isTest
private class {{APEX_PREFIX}}_AccountTriggerHandler_Test {

    @TestSetup
    static void setup() {
        {{TEST_DATA_FACTORY}}.AllowAllConfigSource allowAll = new {{TEST_DATA_FACTORY}}.AllowAllConfigSource();
        // insert test data
    }

    @isTest
    static void testIndustryValidation_blankIndustry_addsError() {
        Account acc = new Account(Name = 'Test', Industry = null);

        Test.startTest();
        Database.SaveResult result = Database.insert(acc, false);
        Test.stopTest();

        System.assertEquals(false, result.isSuccess(), 'Insert should fail for blank Industry');
        System.assertEquals(1, result.getErrors().size(), 'Expected one error on Industry');
        System.assert(
            result.getErrors()[0].getMessage().contains({{APEX_PREFIX}}_AccountConstants.ERROR_INDUSTRY_REQUIRED),
            'Error message mismatch'
        );
    }

    @isTest
    static void testBypass_bypassFlagSet_noValidation() {
        {{APEX_PREFIX}}_TriggerBypass__c bypass = new {{APEX_PREFIX}}_TriggerBypass__c(
            SetupOwnerId = UserInfo.getOrganizationId(),
            Bypass_AccountTrigger__c = true
        );
        insert bypass;

        Account acc = new Account(Name = 'Test', Industry = null);

        Test.startTest();
        Database.SaveResult result = Database.insert(acc, false);
        Test.stopTest();

        System.assertEquals(true, result.isSuccess(), 'Insert should succeed when bypass is active');
    }
}
```

**Test requirements:**
- {{TARGET_COVERAGE}}%+ coverage target; 100% for critical paths.
- Test both bypass-on and bypass-off paths.
- Test bulk scenarios: minimum 200 records to validate governor limit safety.
- Use `{{TEST_DATA_FACTORY}}.AllowAllConfigSource` for config-dependent tests.

---

## Quality Gates

Run before every commit involving triggers or handlers:

```bash
# Static analysis
sf scanner run --target "force-app/main/default/triggers/*.trigger,force-app/main/default/classes/*TriggerHandler*.cls"

# IDOR scan on handler
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py \
    --files {{APEX_PREFIX}}_AccountTriggerHandler.cls \
    --output terminal

# Run trigger handler tests
sf apex test run --class-names {{APEX_PREFIX}}_AccountTriggerHandler_Test --code-coverage --result-format human
```

---

## Pre-Commit Validation Checklist

- [ ] One trigger per object — no duplicate triggers on same SObject
- [ ] Trigger body contains only `new {{APEX_PREFIX}}_<Object>TriggerHandler().run()` — no logic
- [ ] Handler class is named `{{APEX_PREFIX}}_<ObjectName>TriggerHandler`
- [ ] Bypass toggle implemented via Custom Setting or Custom Metadata
- [ ] No SOQL inside any loop
- [ ] No DML inside any loop
- [ ] No empty handler method overrides
- [ ] Recursive prevention implemented if trigger action updates same object
- [ ] `{{LOGGER_CLASS}}` used — no `System.debug()`
- [ ] Test class covers bypass-on and bypass-off paths
- [ ] Test class covers bulk scenario (200 records)
- [ ] Code coverage ≥ {{TARGET_COVERAGE}}%
- [ ] Static analysis clean (no P1/P2/P3 violations)
