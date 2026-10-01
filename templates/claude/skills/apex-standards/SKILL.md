---
name: apex-standards
description: "Apply {{PROJECT_NAME}} Apex coding standards when creating or reviewing Apex classes — security, logging, bulkification, naming, test patterns, and quality gates. Run with: /apex-standards [{{APEX_PREFIX}}_MyClass.cls]"
---

# apex-standards

Apply the full {{PROJECT_NAME}} Apex development standards to a class or review.

**Applies to:** `force-app/**/classes/*.cls`

---

## Security & Data Access

- Always enforce **CRUD/FLS** (Schema Describe or `{{UTILITY_CONTROLLER}}` helpers) and add `WITH SECURITY_ENFORCED` or `WITH USER_MODE` to queries when feasible.
- Default classes to `with sharing`; document any deviation with clear justification in the class header comment.
- Prevent SOQL injection: prefer static queries with bind variables; if dynamic SOQL is unavoidable, **inline** `String.escapeSingleQuotes()` directly in query strings.
- For `@AuraEnabled` methods accepting record IDs: requery with `WITH SECURITY_ENFORCED` to prevent IDOR vulnerabilities.
- Never accept `userId` as a parameter; use `UserInfo.getUserId()` instead.
- **Never expose raw exceptions to API consumers**: in `@RestResource`/`@AuraEnabled` catch blocks, return a generic user-facing error message; log the full stack trace internally via `{{LOGGER_CLASS}}`.

---

## Logging & Exceptions

- Use `{{LOGGER_CLASS}}` via `{{LOGGER_FACTORY}}.getFactory()`.
- Logger variable must be uppercase: `private static final {{LOGGER_CLASS}} LOGGER = ...`
- Prefer typed exceptions; avoid empty catch blocks; never swallow exceptions silently.
- Log level discipline: `LOGGER.debug` for trace points; `LOGGER.info` only for meaningful business events.

---

## Design & Performance

- **Bulkify; zero SOQL/DML in loops.**
- **Null safety**: never dereference map results, query results, or object properties without null checks.
- **Map lookup pattern**: use a single `get()` call followed by a null check; never `containsKey()` + `get()`.
- **REST resource versioning**: every `@RestResource(urlMapping=...)` must include an API version segment (e.g. `/v1/orders/*`).
- **Hardcoded references**: never hardcode IDs, template names, or labels. Use constants, Custom Metadata, or Custom Labels.
- Extract selectors/DAOs; keep service methods small and cohesive.

### Static vs Instance Policy

`static` members are permitted **only** for: constants, stateless pure utility functions, platform-mandated entry points (`@AuraEnabled`/`@InvocableMethod`/`@RestResource`, which must immediately delegate to an instance service), and transaction-scoped caches/recursion guards.

**Anti-patterns (flag in review):** all-static `*Service`/`*Manager`/`*Handler` classes; business logic inside `@AuraEnabled`/`@InvocableMethod`; `static` utilities performing SOQL/DML/logging.

---

## Naming & Style

- Class names start with `{{APEX_PREFIX}}_`.
- Methods: `camelCase` verbs. Constants: `UPPER_SNAKE_CASE`, declared `static final`.

### Class header template

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

---

## Test Class Standards

- **Never use `@IsTest(SeeAllData=true)`**: create test data using `{{TEST_DATA_FACTORY}}` or `@TestSetup`.
- **Always create a test user in `@TestSetup` and use `System.runAs()`**. Use `{{TEST_DATA_FACTORY}}.UserCreator` with a persona/userType string — never hardcode a profile name.
- **Strong assertions**: every test must include meaningful assertions with descriptive failure messages.
- **Coverage quality**: {{TARGET_COVERAGE}}%+ target, {{MIN_COVERAGE}}% minimum to deploy.

---

## Quality Gates & Validation

```bash
sf code-analyzer run --target force-app/main/default/classes/{{APEX_PREFIX}}_MyClass.cls --view detail
sf apex run test --class-names {{APEX_PREFIX}}_MyClassTest --result-format human --code-coverage --wait 10
```

### Pre-Commit Checklist

- [ ] Class header present
- [ ] `with sharing` declared (or documented exception)
- [ ] CRUD/FLS checks present
- [ ] No SOQL/DML in loops
- [ ] Logger present with correct log levels
- [ ] No raw exception messages returned to API consumers
- [ ] No string literals in business logic
- [ ] Unit tests exist, pass, and meet the {{MIN_COVERAGE}}% minimum
- [ ] Test data created via `{{TEST_DATA_FACTORY}}`
