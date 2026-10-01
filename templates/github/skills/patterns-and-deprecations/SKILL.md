---
name: patterns-and-deprecations
description: "Apply {{PROJECT_NAME}} approved design patterns (Selector, Service, Domain, UoW, Strategy), identify anti-patterns, and flag deprecated Apex/LWC features. Run with: /patterns-and-deprecations [file-or-path]"
---

# patterns-and-deprecations

Apply approved design patterns, identify anti-patterns, and flag deprecated features across Apex and LWC.

**Applies to:** `**`

---

## Approved Design Patterns

### Apex Patterns

#### 1. Selector Pattern (SOQL Abstraction)

```apex
// ✅ RECOMMENDED: Encapsulate SOQL in selector classes
public class AccountSelector extends fflib_SObjectSelector {
    public static AccountSelector newInstance() {
        return (AccountSelector) Application.Selector.newInstance(Account.SObjectType);
    }
    public List<Account> selectById(Set<Id> idSet) {
        return Database.query(newQueryFactory().selectFields(new List<String>{'Id', 'Name', 'BillingCity'}).setCondition('Id IN :idSet').toSOQL());
    }
}

// ❌ AVOID: Direct SOQL in Service Classes
public class AccountService {
    public void processAccounts() {
        List<Account> accounts = [SELECT Id, Name FROM Account WHERE Industry = 'Technology']; // ❌
    }
}
```

#### 2. Service Pattern (Business Logic Encapsulation)

```apex
// ✅ RECOMMENDED: Instance-based; never all-static
public with sharing class AccountService {
    public void updateAccountIndustry(Id accountId, String industry) {
        List<Account> accounts = Accounts.newInstance().selectById(new Set<Id>{accountId});
        if (!accounts.isEmpty()) {
            accounts[0].Industry = industry;
            fflib_SObjectUnitOfWork uow = Application.UnitOfWork.newInstance();
            uow.registerDirty(accounts[0]);
            uow.commitWork();
        }
    }
}
```

#### 3. Domain Model Pattern (Object-Oriented Logic)

```apex
// ✅ RECOMMENDED
public class Accounts extends fflib_SObjectDomain {
    public Accounts(List<Account> records) { super(records, Account.SObjectType); }
    public void validateIndustry() {
        for (Account acc : (List<Account>) getRecords()) {
            if (String.isBlank(acc.Industry)) { acc.addError('Industry is required'); }
        }
    }
    public static Accounts newInstance(List<Account> records) { return new Accounts(records); }
}
```

#### 4. Unit of Work Pattern (Transactional Consistency)

```apex
// ✅ RECOMMENDED
fflib_SObjectUnitOfWork uow = Application.UnitOfWork.newInstance();
for (Account acc : accountsToProcess) {
    acc.Status__c = 'Active';
    uow.registerDirty(acc);
}
uow.commitWork();  // Single DML

// ❌ AVOID: DML in loop
for (Account acc : accountsToProcess) {
    update acc;  // 📍 Bad: DML in loop!
}
```

#### 5. Trigger Handler Pattern (Decoupled Business Logic)

```apex
// ✅ MINIMAL trigger — all logic in handler
trigger AccountTrigger on Account (before insert, before update, before delete, after insert, after update, after delete, after undelete) {
    new Accounts_TriggerHandler().run();
}
```

#### 6. Strategy Pattern (Flexible Implementations)

```apex
// ✅ RECOMMENDED: Use interfaces instead of instanceof chains
public interface IAccountProcessor { void process(Account acc); }

public class AccountProcessorFactory {
    public static IAccountProcessor getProcessor(String accountType) {
        switch on accountType {
            when 'Standard' { return new StandardAccountProcessor(); }
            when 'Premium'  { return new PremiumAccountProcessor(); }
            when else { throw new IllegalArgumentException('Unknown account type: ' + accountType); }
        }
    }
}
```

### LWC Patterns

#### 1. Container/Presentational Component Pattern

- **Container**: handles data fetching via `@wire` or imperative calls; emits CustomEvents
- **Presentational**: accepts `@api` data; dispatches CustomEvents upward; no data fetching

#### 2. Event-Driven Communication

```javascript
// Child
this.dispatchEvent(new CustomEvent('itemselected', { detail: { itemId: item.id, itemName: item.name } }));

// Parent
handleItemSelected(event) { const { itemId, itemName } = event.detail; }
```

#### 3. Composition Pattern

```html
<template>
    <c-search-bar placeholder="Search..."></c-search-bar>
    <c-filter-panel filters={availableFilters}></c-filter-panel>
    <c-results-list items={filteredResults}></c-results-list>
    <c-pagination total={totalResults}></c-pagination>
</template>
```

---

## Anti-Patterns to Avoid

### Apex Anti-Patterns

| Anti-pattern | Severity | Fix |
|---|---|---|
| DML in loops | **CRITICAL** | Batch DML outside loops |
| SOQL in loops | **CRITICAL** | Bulk query with IN clause |
| Hardcoded IDs | **Critical** | Query by Name or use constants |
| All-static `*Service`/`*Manager` | **Major** | Instance-based with constructor injection |
| Empty catch blocks | **High** | Log + rethrow; never swallow |
| SOQL without security checks | **High** | `WITH USER_MODE` or `WITH SECURITY_ENFORCED` |
| `containsKey()` + `get()` double lookup | **Minor** | Single `get()` + null check |

### LWC Anti-Patterns

| Anti-pattern | Fix |
|---|---|
| `document.querySelector()` | Use `element.shadowRoot.querySelector()` |
| Magic numbers/strings | Named constants |
| Missing error handling | `try/catch/finally` with toast |
| Event listener memory leaks | Clean up in `disconnectedCallback()` |
| Hardcoded locale (`'en-GB'`) | `import { LOCALE } from '@salesforce/i18n/locale'` |
| `@track` for primitive reassignment | Remove `@track` for simple types |

---

## Salesforce Deprecations

### Apex Deprecations

| Feature | Status | Migration |
|---|---|---|
| Direct String concatenation for SOQL | ❌ Deprecated | Use parameterized queries or fflib Selector |
| `@isTest(seeAllData=true)` | ❌ Bad Practice | Use explicit test data setup |
| `System.debug()` without logger | ❌ Deprecated | Use `{{LOGGER_CLASS}}` (project standard) |
| Custom test data factories | ⚠️ Discouraged | Use `{{TEST_DATA_FACTORY}}` pattern |
| Hard-coded Org IDs | ❌ Anti-Pattern | Use environment-aware configuration |

### LWC Deprecations

| Feature | Status | Migration |
|---|---|---|
| `if:true` / `if:false` | ❌ Legacy | Use `lwc:if`, `lwc:elseif`, `lwc:else` (API v58.0+) |
| `lwc:dom="manual"` | ⚠️ Limited Use | Use standard template rendering |
| `@track` for primitive reassignment | ⚠️ Unnecessary | Remove for `string`, `number`, `boolean` |
| Custom CSS overrides of SLDS | ❌ Bad Practice | Use SLDS utility classes and CSS custom properties |
| Hardcoded locale strings | ⚠️ Non-Localized | Import from `@salesforce/i18n/locale` |

---

## Biased Terminology (`AvoidTermsWithImplicitBias`)

Never use these terms in code, comments, documentation, or metadata:

| Banned term | Use instead |
|---|---|
| `whitelist` | `allowlist` |
| `blacklist` | `denylist` / `blocklist` |
| `blackout` | `service outage` / `outage window` |
| `brownout` | `degraded service` / `throttle` |
| `slave` | `replica` / `secondary` / `worker` |

Applies to: Apex identifiers, SOQL, LWC JS/HTML, Flow labels, custom object/field API names, string literals, and all documentation.

---

## Code Quality Standards

### Coverage Requirements

- **Minimum**: {{MIN_COVERAGE}}% for deployment
- **Target**: {{TARGET_COVERAGE}}%+ for production-ready code
- **Critical paths**: 100% for security, payment, data integrity logic

### Assertion Quality Standards

```apex
// ❌ WEAK
System.assertEquals(2, result.size());

// ✅ STRONG: Clear, descriptive assertion with context
System.assertEquals(2, result.size(), 'Expected 2 active accounts but got ' + result.size() + ' | Test Data: ' + accountIds);
```

---

## Pre-Commit Validation

1. ✅ Run **ESLint** / **Salesforce Code Analyzer** (Apex & LWC)
2. ✅ Run **Jest tests** with coverage reporting
3. ✅ Run **IDOR security scanner** (if Apex controllers present)
4. ✅ Review code for anti-patterns listed above
5. ✅ Verify **test coverage >= {{MIN_COVERAGE}}%** (minimum)
6. ✅ Ensure **no deprecated patterns** without migration plan
