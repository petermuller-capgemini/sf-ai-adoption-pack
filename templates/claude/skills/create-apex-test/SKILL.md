---
name: create-apex-test
description: "Create or update an Apex test class for a given class following {{PROJECT_NAME}}'s testing standard — persona-based two-user pattern, System.runAs(), {{TARGET_COVERAGE}}% coverage. Run with: /create-apex-test [ClassName or path]"
---

# create-apex-test

Create or update an Apex test class for a given class in this project following the two-user testing standard.

## Steps

1. **Read the target class** to understand all public/global methods and branches to cover.

2. **Choose the correct persona constant** from the table below. Match the persona to the actor that drives the class under test. Never use a hardcoded profile name like `'System Administrator'`.

   | Constant | Persona | When to use |
   |---|---|---|
   | `'systemAdmin'` | System Administrator | `@TestSetup` fixture creation only — never for test execution |
   | `'standardUser'` | Standard internal user | Typical internal-facing controllers and business logic |
   | `'restrictedUser'` | Restricted-access user | Negative tests verifying CRUD/FLS enforcement |
   | `'integrationUser'` | System/integration user | REST API endpoints, inbound integrations, auth providers |
   | `'guestUser'` | Guest / unauthenticated user | Public-facing guest or self-service flows |
   | `'eventSubscriber'` | Platform Event subscriber | Platform event handlers, strategy classes |

   The persona string is config-driven via `{{CONFIG_PREFIX}}_CodeMapping__mdt` and resolves profile/Permission Set Group/permission sets automatically.

   **Permission conflict check:** If the user story modifies a Permission Set Group or any of its member permission sets that the chosen persona uses, switch to a persona whose Permission Set Group is NOT in the branch (`git status --short force-app/main/default/permissionsetgroups/ force-app/main/default/permissionsets/`). Mapping is in `force-app/main/default/customMetadata/{{CONFIG_PREFIX}}_CodeMapping.{{CONFIG_PREFIX}}_UnitTestConfig.md-meta.xml`.

3. **Write the test class** following the mandatory Two-User Pattern:

```apex
/**
 * @description       : Test class for <ClassName>. <One-sentence summary of what is covered.>
 * @author            : <Full Name>
 * @last modified on  : DD-MM-YYYY
 * @last modified by  : <Full Name>
 * Modifications Log
 * Ver   Date         Author       Modification
 * 1.0   DD-MM-YYYY   <Full Name>  Initial Version
 **/
@IsTest
private with sharing class {{APEX_PREFIX}}_<ClassName>Test {

    private static User sysAdminUser;       // For fixture creation
    private static User personaTestUser;    // For System.runAs() test execution

    @TestSetup
    static void setupData() {
        // Create System Admin user for fixture setup (runs at sysadmin level, outside System.runAs)
        sysAdminUser = new {{TEST_DATA_FACTORY}}.UserCreator('systemAdmin', 'Setup')
            .setFirstName('Test')
            .create();

        // Create Persona-based user for actual test execution under System.runAs
        personaTestUser = new {{TEST_DATA_FACTORY}}.UserCreator('<userType>', 'TestUser')
            .setFirstName('Test')
            .create();

        // Create test fixtures outside System.runAs so they run at sysadmin level
        System.runAs(sysAdminUser) {
            // Create baseline test data (accounts, orders, etc.)
        }
    }

    @IsTest
    static void should_DoSomething_WhenCondition() {
        User testUser = [SELECT Id FROM User WHERE LastName = 'TestUser' AND IsActive = true WITH USER_MODE LIMIT 1];

        System.runAs(testUser) {
            // arrange
            Test.startTest();
            // act
            Test.stopTest();
            // assert — specific values, not just assertNotEquals(null, result)
            System.assertEquals(expected, actual, 'Descriptive assertion message');
        }
    }
}
```

### Why Two Users?

- **System Admin user** (in `@TestSetup`): Creates test fixtures/test data outside `System.runAs()`. Efficient and avoids permission issues during setup.
- **Persona user**: Executes the actual test method code inside `System.runAs()`. Validates that code works under the intended persona's permissions, not just System Admin privileges.

This ensures:
1. Test fixtures are created efficiently without permission constraints.
2. The code under test runs under realistic persona permissions (validating CRUD/FLS enforcement).
3. You catch permission-related bugs that only appear in production under that persona.

4. **Coverage target**: aim for ≥ {{TARGET_COVERAGE}}% of lines. Cover every branch in `if`/`else` blocks, both empty-list and non-empty-list paths, and every public method.

5. **Do not push until you have compared local files with the org** (see your project's deployment workflow documentation).

---

## Rules

- Every test method body must be wrapped in `System.runAs(testUser)`.
- All SOQL inside `System.runAs` blocks must include `WITH USER_MODE`.
- `@TestSetup` creates both users once; test methods query persona user by `LastName = 'TestUser'`.
- Never insert a user directly inside a test method body (causes duplicate-username `DMLException` on re-runs).
- Never call legacy one-off user-creation helpers — route all test user creation through the factory.
- Use `new {{TEST_DATA_FACTORY}}.UserCreator(userType, lastName)` — never hardcode a profile name.
- API version in the `*-meta.xml` must be `{{SF_API_VERSION}}`.
- If `@TestSetup` needs existing SObject data (e.g., pre-seeded Accounts), insert it inside `System.runAs(sysAdminUser)` so it runs at sysadmin level, then query it inside each test's `System.runAs(personaTestUser)` block.
