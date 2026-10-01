---
name: security-standards
description: "Apply OWASP Top 10 and {{PROJECT_NAME}} security standards to Apex, LWC, and Salesforce configuration — access control, injection, cryptography, and auth. Run with: /security-standards [file-or-path]"
---

# security-standards

Apply {{PROJECT_NAME}} security standards based on OWASP Top 10 to Apex, LWC, and Salesforce configuration.

**Applies to:** `**`

---

## A01: Broken Access Control

```apex
// CORRECT: enforce sharing + USER_MODE
public with sharing class OrderController {
    @AuraEnabled
    public static List<Order__c> getOrders() {
        return [SELECT Id, Name FROM Order__c WITH USER_MODE];
    }
}
```

**IDOR prevention:** never trust a record Id from user input without verifying access via `WITH USER_MODE` or an explicit CRUD/FLS check.

**SSRF prevention:** never pass user-controlled values to callout endpoints — use Named Credentials only.

---

## A02: Cryptographic Failures

| Algorithm | Status | Use instead |
|---|---|---|
| MD5 / SHA-1 | Prohibited | SHA-256 / SHA-512 |
| DES / 3DES | Prohibited | AES-256 |
| AES-128 (ECB) | Prohibited | AES-256 (CBC/GCM with IV) |

Never store plaintext passwords, tokens, or PII in custom fields. Use Named Credentials for external credentials. Mask PII in log output via `{{LOGGER_CLASS}}`.

---

## A03: Injection

All dynamic SOQL must use bind variables. In LWC, use `textContent` (not `innerHTML`) for user-controlled content, or sanitize with DOMPurify first.

---

## A05: Security Misconfiguration

```apex
// Default to with sharing
public with sharing class UtilityHelper { ... }

// Deviation requires explicit justification
// Without sharing required: <reason>, confirmed with security lead <date>
public without sharing class {{APEX_PREFIX}}_ReportingService { ... }
```

Org checklist: My Domain enabled, HTTPS enforced, guest user profile minimal, Login IP Ranges enforced for integration profiles.

---

## A07: Authentication and Session Management

- Never build custom auth — use Salesforce platform authentication (SSO, MFA, OAuth 2.0).
- Integration users: use Named Credentials + OAuth client credentials flow — never username/password in code.
- Never log session tokens; log a masked/hashed identifier only.

---

## A08: Software and Data Integrity Failures

- All deployments must go through {{CICD_TOOL}} — no direct org deployment outside the pipeline.
- Validate all inbound webhook/API payloads before processing.
- Review third-party managed package permissions before installation.

---

## Language & Terminology

Never use biased terminology (`whitelist`/`blacklist`/`slave` etc.) in code, comments, metadata, or docs — use `allowlist`/`denylist`/`replica` instead.

## Agent Protocol

Use `vscode_askQuestions` for any clarification needed mid-task rather than stopping. Delegate heavy analysis to subagents and instruct them to return only key findings.
