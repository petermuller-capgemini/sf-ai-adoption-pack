---
name: gdpr-compliance
description: "Apply UK GDPR compliance requirements to Salesforce code — PII classification, data masking, retention policies, deletion patterns, and compliance checklists. Run with: /gdpr-compliance [file-or-path]"
---

# gdpr-compliance

Apply UK GDPR and data protection requirements to Salesforce platform code and metadata.

**Applies to:** `**`

---

## Overview

All code handling personal data must comply with UK GDPR requirements for:
- **Right to be Forgotten**: Individual data deletion
- **Data Minimization**: Collection and retention limits
- **Data Security**: Masking and encryption of PII
- **Transparency**: Clear data processing documentation
- **Portability**: Subject Access Request (SAR) support

---

## Personal Data (PII) Classification

### High-Sensitivity PII (Requires Field-Level Encryption)
- Payment card numbers (use Shield Platform Encryption)
- Government IDs (passport, driver's license)
- Health information
- Financial account details
- Social security numbers

### Standard PII (Requires Protection)
- Email addresses (`Contact.Email`, `Lead.Email`)
- Phone numbers (`Contact.Phone`, `Lead.Phone`)
- Physical addresses (`Contact.MailingAddress`)
- Name fields (`FirstName`, `LastName`)
- Date of birth
- IP addresses (stored in logs)
- Identity provider tokens (SSO / B2C)

### Pseudonymous Data (Lower Risk)
- Salesforce Record IDs (18-character)
- Case numbers
- Order numbers (external reference)
- Anonymized analytics data

---

## Data Retention Policies

### Standard Objects

| Object | Retention Period | Legal Basis |
|--------|------------------|-------------|
| `Account` (active) | Account lifetime + 90 days | Business requirement |
| `Account` (inactive) | 3 years from last activity | GDPR minimization |
| `Contact` (inactive) | 3 years from last interaction | GDPR minimization |
| `Lead` (unconverted) | 2 years from creation | Marketing necessity |
| `Case` (closed) | 6 years from closure | Legal compliance |
| `Order` | 7 years from creation | Financial/tax law (never delete) |
| `EmailMessage` | 90 days from send | Technical necessity |
| `ContentVersion` | 7 years from upload | Document retention |

### Custom Objects

| Object | Retention Period |
|--------|------------------|
| `{{APEX_PREFIX}}_CustomerPreference__c` | Until consent withdrawn + 30 days |
| `{{APEX_PREFIX}}_PaymentToken__c` | Transaction + 90 days |
| `{{APEX_PREFIX}}_AuditLog__c` | 7 years |
| `{{APEX_PREFIX}}_MarketingConsent__c` | Until withdrawn + 30 days |
| `{{APEX_PREFIX}}_SessionData__c` | 24 hours |

---

## Data Masking Patterns

### Apex Masking Utility — `{{APEX_PREFIX}}_DataMaskingUtil`

```apex
public static String maskEmail(String email) {
    if (String.isBlank(email) || !email.contains('@')) { return '***@***.***'; }
    List<String> parts = email.split('@');
    String localPart = parts[0];
    String maskedLocal = localPart.length() > 2
        ? localPart.substring(0, 1) + '***' + localPart.substring(localPart.length() - 1)
        : '***';
    List<String> domainParts = parts[1].split('\\.');
    String maskedDomain = domainParts[0].length() > 2
        ? domainParts[0].substring(0, 1) + '***' + domainParts[0].substring(domainParts[0].length() - 1)
        : '***';
    return maskedLocal + '@' + maskedDomain + '.' + domainParts[domainParts.size() - 1];
}

public static String maskPhone(String phone) {
    if (String.isBlank(phone) || phone.length() < 4) { return '****'; }
    String digitsOnly = phone.replaceAll('[^0-9]', '');
    return '****' + digitsOnly.substring(digitsOnly.length() - 4);
}

public static String maskCreditCard(String cardNumber) {
    if (String.isBlank(cardNumber) || cardNumber.length() < 4) { return '****-****-****-****'; }
    String digitsOnly = cardNumber.replaceAll('[^0-9]', '');
    return '****-****-****-' + digitsOnly.substring(digitsOnly.length() - 4);
}
```

### Usage in controllers

```apex
// ✅ CORRECT: Log with masked PII
LOGGER.info('Retrieved customer info for: {0}', new Object[]{ {{APEX_PREFIX}}_DataMaskingUtil.maskEmail(customer.Email) });

// ❌ AVOID: Logging full PII
// LOGGER.debug('Customer email: ' + customer.Email);
```

### Platform Event Masking

```apex
// ✅ CORRECT: Mask PII in platform events
{{APEX_PREFIX}}_CustomerDeletionEvent__e event = new {{APEX_PREFIX}}_CustomerDeletionEvent__e(
    CustomerID__c = contact.Id,
    AnonymizedEmail__c = {{APEX_PREFIX}}_DataMaskingUtil.maskEmail(contact.Email),
    DeletionTimestamp__c = System.now(),
    DeletionReason__c = 'GDPR Right to be Forgotten'
);
EventBus.publish(event);
```

---

## Data Deletion Implementation

### Batch Deletion Pattern

```apex
global class {{APEX_PREFIX}}_DeleteInactiveContactsBatch implements Database.Batchable<sObject>, Database.Stateful {
    private static final {{LOGGER_CLASS}} LOGGER = {{LOGGER_FACTORY}}.getFactory().createBatchedLogger('{{APEX_PREFIX}}_DeleteInactiveContactsBatch');
    private Integer retentionDays;

    global Database.QueryLocator start(Database.BatchableContext bc) {
        Date cutoffDate = System.today().addDays(-retentionDays);
        return Database.getQueryLocator([
            SELECT Id, Email, FirstName, LastName FROM Contact
            WHERE LastActivityDate < :cutoffDate
            AND IsDeleted = false
            AND {{APEX_PREFIX}}_DoNotDelete__c = false
            WITH USER_MODE
        ]);
    }

    global void execute(Database.BatchableContext bc, List<Contact> scope) {
        List<Contact> toAnonymize = new List<Contact>();
        for (Contact con : scope) {
            // Archive to Big Object BEFORE anonymization
            // Then anonymize (don't delete — preserves referential integrity)
            con.Email = 'deleted_' + con.Id + '@anonymized.local';
            con.FirstName = 'Deleted';
            con.LastName = 'User';
            con.Phone = null;
            con.MobilePhone = null;
            con.MailingStreet = null;
            con.Birthdate = null;
            con.Description = '[GDPR Deletion - ' + System.now().format() + ']';
            toAnonymize.add(con);
        }
        Database.update(toAnonymize, false);
        LOGGER.publishBatchedLogEvents();
    }
}
```

### Right to be Forgotten (Manual Request)

```apex
public with sharing class {{APEX_PREFIX}}_GDPRController {
    @AuraEnabled
    public static void deleteMyData() {
        Id userId = UserInfo.getUserId();
        User currentUser = [SELECT ContactId FROM User WHERE Id = :userId WITH USER_MODE LIMIT 1];
        if (currentUser.ContactId == null) {
            throw new AuraHandledException('No customer record found');
        }
        System.enqueueJob(new {{APEX_PREFIX}}_AnonymizeContactQueueable(currentUser.ContactId));
        LOGGER.info('GDPR deletion request submitted by User: {0}, Contact: {1}', new Object[]{ userId, currentUser.ContactId });
    }
}
```

---

## Common Anti-Patterns

```apex
// ❌ Storing sensitive data in plain text
Contact.{{APEX_PREFIX}}_CreditCard__c = '4111111111111111';

// ❌ Logging PII in production
System.debug('Customer email: ' + contact.Email);
LOGGER.info('Processing: ' + contact.Email);  // Use maskEmail() instead

// ❌ Deleting instead of anonymizing
delete [SELECT Id FROM Contact WHERE LastActivityDate < :cutoffDate];
// Should anonymize to preserve referential integrity

// ❌ Hardcoded retention periods
Integer retentionDays = 9999;  // Use Custom Metadata instead
```

---

## Compliance Checklist

**Before deploying Salesforce code:**

- [ ] All PII fields have CRUD/FLS checks in Apex
- [ ] Sharing rules configured per data classification
- [ ] Masking applied to logs, debug statements, platform events
- [ ] Deletion/anonymization logic tested for cascade integrity
- [ ] Big Objects configured for long-term audit archive
- [ ] GDPR batch jobs scheduled and monitored
- [ ] Marketing consent uses checkbox (not pre-selected)
- [ ] Privacy policy linked on data collection forms
- [ ] Data export capability available (Subject Access Request)
- [ ] Custom metadata retention policies defined

**Code Review Focus:**
- Search for `Contact.Email`, `Lead.Phone`, `Account.BillingAddress`
- Verify no PII in `System.debug()` statements
- Check Big Object archival before deletion
- Validate `WITH USER_MODE` or explicit CRUD/FLS checks
- Ensure error messages don't leak PII

---

## Custom Metadata for Retention Policies

Use `{{APEX_PREFIX}}_RetentionPolicy__mdt` with fields:
- `ObjectName__c` (Account, Contact, Lead)
- `RetentionDays__c` (1095 for 3 years)
- `AutoDelete__c` (true/false)
- `ArchiveBeforeDelete__c` (true/false)

```apex
public static Integer getRetentionDays(String objectName) {
    {{APEX_PREFIX}}_RetentionPolicy__mdt policy = [
        SELECT RetentionDays__c FROM {{APEX_PREFIX}}_RetentionPolicy__mdt WHERE ObjectName__c = :objectName LIMIT 1
    ];
    return policy != null ? Integer.valueOf(policy.RetentionDays__c) : 1095;
}
```

---

**Remember:** GDPR compliance is not optional. Every Apex class, LWC component, and Flow handling personal data requires documented legal basis, retention policy, and deletion mechanism. When in doubt, consult legal/privacy teams before implementation.
