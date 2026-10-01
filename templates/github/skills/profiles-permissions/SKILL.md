---
name: profiles-permissions
description: "Apply {{PROJECT_NAME}} Profile, Permission Set, and Permission Set Group naming, structure, and least-privilege standards. Run with: /profiles-permissions [file-or-path]"
---

# profiles-permissions

Apply project standards for Profiles, Permission Sets, and Permission Set Groups.

**Applies to:** `force-app/**/permissionsets/**, force-app/**/permissionsetgroups/**, force-app/**/profiles/**`

---

## Principles

- **Least privilege** — grant only the permissions required for a specific function.
- **Single responsibility** — one Permission Set = one capability, not a job role.
- **Composable access** — combine reusable Permission Sets; never create monolithic ones.
- **Predictable structure** — consistent naming enables maintenance, testing, and automation.
- **Automated assignment** — support joiner/mover/leaver provisioning via User Access Policies (UAPs).

---

## Profiles

Profiles are licence-specific access shells. All meaningful permissions must be granted via Permission Sets, not Profiles.

### Rules

- **Never use standard profiles.** All users must be assigned custom profiles.
- **Clone from Minimum Access profiles** only (if unmodified):
  - Salesforce licence → clone `Minimum Access – Salesforce`
  - Salesforce Integration licence → clone `Minimum Access – API Only Integrations`
- **Profile-level settings allowed** (until Salesforce provides alternatives):
  - Login Hours, Login IP Ranges
  - Default Record Types, Default Apps
  - Page Layout Assignments (prefer dynamic forms)
  - Session Settings, Password Policies (where different from org-wide defaults)
- **All other access** (OLS, FLS, Apex/Flow access, system permissions) → **Permission Sets only**.

### Naming Convention

```
<Licence Prefix>: <Profile Descriptor>
```

| Salesforce Licence | Prefix |
|---|---|
| Salesforce | `SF` |
| Salesforce Platform | `SP` |
| Salesforce Integration | `SI` |
| Identity | `ID` |
| Customer Community Login | `CCL` |
| Customer Community Plus | `CCP` |
| Customer Community Plus Login | `CPL` |
| Partner Community | `PC` |
| External Apps | `EA` |
| External Apps Login | `EAL` |
| External Identity | `EI` |

**Examples:** `SF: Internal`, `SF: Administrator`, `SI: Integrations`, `SI: ServiceNow`

### Anti-Patterns

```xml
<!-- ❌ AVOID: Using standard profiles -->
<!-- ❌ AVOID: Granting object/field permissions on profiles -->
<!-- ❌ AVOID: Using profiles to differentiate UI — use dynamic forms instead -->

<!-- ✅ CORRECT: Minimal custom profile cloned from Minimum Access -->
<!-- All OLS/FLS/Apex/System permissions granted via Permission Sets -->
```

---

## Permission Sets

### Design Checklist

Before creating a Permission Set, verify:
- [ ] Can I describe its purpose in one clear sentence?
- [ ] Does it represent a capability, not a job title?
- [ ] Is the scope intentionally small and focused?
- [ ] Could this be reused across personas?
- [ ] Does it overlap with an existing Permission Set?
- [ ] Is privileged access isolated in its own Permission Set?

### Permission Set Types

| Type | Prefix | Description | Contains |
|------|--------|-------------|----------|
| **Data Access** | `Obj` | Object-level and field-level access for a single object | Separate PSs for: Read (`R`), Read/Create/Update (`CRU`), Delete (`D`). No highly-confidential fields. No tab access. |
| **Sensitive Data Access** | `ObjS` | Access to highly-confidential fields | Isolated per object; only sensitive fields |
| **Special Access — Connected App** | `ConA` | Connected App access | Single Connected App per PS |
| **Special Access — Custom Permission** | `CusP` | Custom Permission access | Single Custom Permission per PS |
| **Special Access — External Credential** | `ExtC` | External Credential access | Must include Read OLS on `UserExternalCredential` |
| **Functional** | `Func` | Business capability access | Apps, Tabs, OLS/FLS (minimum), Flow/Apex access, App Permissions, Custom Metadata, Custom Settings, PS Licences |
| **Privileged** | `Sys` | Elevated system permissions | Isolated individually or in very small groups; never duplicated |

### Naming Convention

```
<Type Prefix>: <Capability>[: <Access Qualifier>]
```

**Examples:**

| Permission Set Name | Description |
|---|---|
| `Obj: Case: R` | Read-only access to Case object and core fields |
| `Obj: Case: CRU` | Read, Create, Update access to Case |
| `Obj: Case: D` | Delete access to Case with minimal Read FLS |
| `ObjS: Case: R` | Read-only access to sensitive Case fields |
| `ConA: Dataloader.io` | Access to dataloader.io Connected App |
| `CusP: Allow MFA Reset` | MFA reset functionality access |
| `ExtC: PaymentGateway` | PaymentGateway External Credential access |
| `Func: Reopen Case` | Capability to reopen closed cases |
| `Sys: API Enabled` | API Enabled system permission |

### Anti-Patterns

```xml
<!-- ❌ AVOID: Single monolithic Permission Set per role -->
<!-- ❌ AVOID: Mixing functional and privileged permissions -->
<!-- ❌ AVOID: Duplicated permissions across Permission Sets -->
<!-- ❌ AVOID: "God" Permission Sets with ViewAllData + ModifyAllData + ... -->

<!-- ✅ CORRECT: Single-capability, reusable Permission Set -->
<PermissionSet>
    <label>Obj: Case: CRU</label>
    <description>Read, Create and Update access to the Case object and core fields.</description>
    <objectPermissions>
        <object>Case</object>
        <allowRead>true</allowRead>
        <allowCreate>true</allowCreate>
        <allowEdit>true</allowEdit>
    </objectPermissions>
</PermissionSet>
```

### Additional Rules

- **Licence association**: most Permission Sets should be licence-agnostic for reuse.
- **Session-activated Permission Sets**: encouraged for transactional access.

---

## Permission Set Groups

Permission Set Groups collate Permission Sets into logical bundles. **Preferred assignment mechanism** — assign groups, not individual Permission Sets.

### Permission Set Group Types

| Type | Prefix | Description |
|------|--------|-------------|
| **Persona** | `Pers` | Represents a job role; bundles all base permissions for a user's work activities |
| **Functional** | `Func` | Bundles multiple Permission Sets for a business capability reusable across personas |
| **Privileged** | `Priv` | Discrete privileged permissions for temporary assignment via PAM |

### Naming Convention

```
<Type Prefix>: <Descriptor> PSG
```

**Examples:**

| Permission Set Group Name | Type |
|---|---|
| `Pers: Support Agent PSG` | Persona |
| `Func: Order Management PSG` | Functional |
| `Priv: Manage Users PSG` | Privileged |

### Functional PSG Rules

Create a Functional PSG when the function spans multiple objects, requires multiple independent capabilities, or may be reused across multiple personas. Must **not** contain persona-based or privileged permissions.

### Muting Permission Sets

Use sparingly. Extensive muting indicates Permission Sets need refactoring.

### Anti-Patterns

```xml
<!-- ❌ AVOID: Mixed-purpose groups (persona + functional + privileged) -->
<!-- ❌ AVOID: Individual-specific groups ("John Smith PSG") -->

<!-- ✅ CORRECT: Persona group with composable Permission Sets -->
<PermissionSetGroup>
    <label>Pers: Support Agent PSG</label>
    <description>Bundles all capabilities for Support Agent users.</description>
    <permissionSets>
        <permissionSet>Obj_Account_CRU</permissionSet>
        <permissionSet>Obj_Case_CRU</permissionSet>
        <permissionSet>{{APEX_PREFIX}}_Case_Management</permissionSet>
        <permissionSet>Sys_Lightning_Experience_User</permissionSet>
    </permissionSets>
</PermissionSetGroup>
```

---

## User Access Policies (UAPs)

- All Personas **must** include UAPs for automated provisioning.
- The `User` object must include a **Persona custom picklist field** populated during joiner/mover/leaver user creation.
- UAPs assign Permission Set Groups, public groups, and queues based on profile or persona field.

---

## Required Org Settings

Enable in **User Management Settings**:
- Field-Level Security for Permission Sets during Field Creation ✅ (Required)
- Permission Set & Permission Set Group Assignments with Expiration Dates ✅ (Required)
- User Access Policies ✅ (Required)

---

## Documentation Requirements

Every Profile, Permission Set, and Permission Set Group **must** have a clear, concise `description` field explaining purpose and scope.

---

## Code Review Checklist

- [ ] Naming follows convention: `<Prefix>: <Descriptor>` (and `PSG` suffix for groups)
- [ ] No OLS/FLS/Apex/system permissions on Profiles
- [ ] Permission Sets follow single-responsibility principle
- [ ] Privileged permissions (`ModifyAllData`, `ViewAllData`, `ManageUsers`) are in `Sys:` Permission Sets only
- [ ] No duplicated permissions across Permission Sets without justification
- [ ] Sensitive field access is in `ObjS:` Permission Sets only
- [ ] Permission Set Groups have correct type prefix (`Pers`, `Func`, `Priv`)
- [ ] Description field is populated and meaningful
- [ ] Muting is minimal and justified
