---
name: configuration-standards
description: "Apply {{PROJECT_NAME}} standards for Custom Settings, Custom Labels, Validation Rules, Flexipages, and Experience Cloud Sites — naming, security, deduplication. Run with: /configuration-standards [file-or-path]"
---

# configuration-standards

Apply secure and maintainable configuration practices for Salesforce metadata.

**Applies to:** `force-app/**/objects/**/customSettings/**, force-app/**/labels/**, force-app/**/validationRules/**, force-app/**/flexipages/**, force-app/**/sites/**`

---

## 1. Custom Settings

### Security

- **Never store encryption keys in plain text** — use Named Credentials or Protected Custom Metadata Types for secrets.
- If Custom Settings must store crypto keys, use Platform Encryption.
- Audit access to Custom Settings containing sensitive data (limit to System Administrators).

```xml
<!-- ❌ Plain text crypto key visible to all users with access -->
<fields>
    <fullName>{{CONFIG_PREFIX}}_key__c</fullName>
    <type>Text</type>
</fields>

<!-- ✅ Use Protected Custom Metadata Type or Named Credential instead -->
```

### Naming conventions

- Start with `{{CONFIG_PREFIX}}_`, use PascalCase with underscores: `{{CONFIG_PREFIX}}_Automation_Settings__c`
- Fields start with `{{CONFIG_PREFIX}}_` and use consistent capitalization: `{{CONFIG_PREFIX}}_Key__c` (not `{{CONFIG_PREFIX}}_key__c`)

```
❌ LogManagement__c                   (missing prefix)
❌ {{CONFIG_PREFIX}}AccountSetting__c (no underscores)
✅ {{CONFIG_PREFIX}}_Log_Management__c
✅ {{CONFIG_PREFIX}}_Account_Settings__c
```

### Documentation

Every Custom Setting must have a description explaining purpose, field descriptions for all fields, and a change log (who created, when, why).

### Eliminate duplicates

Before creating a Custom Setting, search for existing settings with similar purpose. Merge duplicate settings; use a single setting with multiple fields rather than multiple settings.

---

## 2. Custom Labels

### No hardcoded IDs

**Never store Salesforce IDs in Custom Labels** — IDs vary between orgs.

```apex
// ❌ Profile ID differs per org
externalProfileId = 00e000000000000AAA

// ✅ Runtime lookup by name
Profile externalProfile = [SELECT Id FROM Profile WHERE Name = 'My External Profile' LIMIT 1];
```

### Environment-agnostic URLs

**Never hardcode environment-specific URLs** — use `Site.getBaseUrl()`, `URL.getSalesforceBaseUrl()`, or Custom Metadata.

```apex
// ❌ Environment-specific
{{CONFIG_PREFIX}}_SsoUrl = https://mycompany--qa.sandbox.my.site.com/...

// ✅ Dynamic
String ssoUrl = Site.getBaseUrl() + '/services/auth/sso/MyAuthProvider';
```

### Eliminate duplicates

Merge duplicate labels with identical values. Values appearing 5+ times (e.g. a support phone number) should live in one label: `{{CONFIG_PREFIX}}_Customer_Service_Phone`.

### Remove unused labels

Audit labels quarterly:
```bash
grep -r "Label.{{CONFIG_PREFIX}}_Some_Label_Name" force-app/
# If no results, delete the label
```

### Naming convention

- Start with `{{CONFIG_PREFIX}}_`
- Descriptive PascalCase: `{{CONFIG_PREFIX}}_Terms_Conditions_URL`
- Avoid abbreviations

---

## 3. Validation Rules

### Bypass control

Every validation rule should reference bypass settings for data loads and admin overrides:

```
Rule Name: {{CONFIG_PREFIX}}_Account_Billing_Address_Required
Error Condition Formula:
AND(
  NOT($Setup.{{CONFIG_PREFIX}}_Automation_Settings__c.{{CONFIG_PREFIX}}_Bypass_Validation_Rules__c),
  NOT($Permission.{{CONFIG_PREFIX}}_Override_Validation_Rules),
  ISBLANK(BillingStreet)
)
```

### Record type checks

Include record type in formula when rule applies to specific types.

### Custom Permissions over profile checks

```
// ❌ Brittle
NOT($Profile.Name = 'System Administrator')

// ✅ Flexible
NOT($Permission.{{CONFIG_PREFIX}}_Override_Account_Validation)
```

### Remove inactive rules

Delete validation rules that are inactive and no longer needed.

### Documentation

Every validation rule must have: description of business rule, example of invalid data, and bypass mechanism documented.

---

## 4. Flexipages (Lightning Pages)

### Naming convention

Pattern: `{{CONFIG_PREFIX}}_<Object>_<PageType>_Page`

```
✅ {{CONFIG_PREFIX}}_Account_Record_Page
✅ {{CONFIG_PREFIX}}_Case_Record_Page
❌ Account_Record_Page1    (no prefix)
```

### Eliminate duplicates

Consolidate duplicate pages — determine which is active, delete the other.

### Required description

```
Description: Customized Account record page with payment integration component.
Assigned To: <record type / app / profile>
Owner: <owning team>
```

### Assignment review

Verify page assignments: correct record types, apps, or profiles.

---

## 5. Experience Cloud Sites

### Guest user security

**Default: disable guest access unless required.**

Checklist for sites with guest access:
- [ ] Guest user profile has **read-only** access to exposed objects
- [ ] No PII or sensitive fields accessible to guest user
- [ ] No Create/Update/Delete permissions for guest user
- [ ] IP restrictions configured if possible
- [ ] Guest user sharing rules limit record visibility
- [ ] Apex controllers use `with sharing` and validate `UserInfo.getUserType()`

```apex
// ✅ Verify user type in controllers with guest access
public with sharing class {{APEX_PREFIX}}_ExternalReportingController {
    @AuraEnabled
    public static List<Report_Data__c> getReports() {
        if (UserInfo.getUserType() == 'Guest') {
            return [SELECT Id, Name FROM Report_Data__c WHERE {{CONFIG_PREFIX}}_Is_Public__c = true WITH SECURITY_ENFORCED];
        }
        return [SELECT Id, Name, {{CONFIG_PREFIX}}_Details__c FROM Report_Data__c WITH SECURITY_ENFORCED];
    }
}
```

### Site security checklist

- [ ] Guest access disabled unless documented requirement exists
- [ ] All Apex controllers use `with sharing` and validate `UserInfo.getUserType()`
- [ ] No PII fields exposed to guest user profile
- [ ] Content Security Policy (CSP) configured
- [ ] HTTPS enforced
- [ ] Session timeout configured appropriately

---

## Quality Gates & Validation

### Custom Settings security audit

```bash
grep -r "key__c\|password__c\|secret__c" force-app/main/default/objects/**/fields/*.field-meta.xml
```

### Custom Labels environment check

```bash
# Search for hardcoded IDs
grep -E "[0-9]{15,18}" force-app/main/default/labels/CustomLabels.labels-meta.xml

# Search for environment-specific URLs
grep -E "sandbox|--qa|--uat" force-app/main/default/labels/CustomLabels.labels-meta.xml
```

### Validation Rule coverage check

```bash
# Verify bypass controls exist
grep -r "{{CONFIG_PREFIX}}_Automation_Settings__c" force-app/main/default/objects/**/validationRules/*.validationRule-meta.xml | wc -l

# Find inactive rules
grep -r "<active>false</active>" force-app/main/default/objects/**/validationRules/*.validationRule-meta.xml
```

### Pre-Deployment Configuration Checklist

- [ ] No duplicate Custom Settings; all have descriptions; no plain-text secrets; naming `{{CONFIG_PREFIX}}_<Name>__c`
- [ ] No hardcoded IDs or environment-specific URLs in labels; no duplicate labels; unused labels removed
- [ ] Validation rules have bypass controls, record type checks where applicable, custom permissions (not profiles); inactive rules deleted
- [ ] Flexipages have `{{CONFIG_PREFIX}}_` prefix, no unjustified duplicates, all have descriptions, assignments verified
- [ ] Experience Cloud sites: guest access disabled unless required; guest profile permissions audited; Apex controllers secured; CSP and HTTPS configured
