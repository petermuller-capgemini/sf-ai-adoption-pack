---
applyTo: "*"
description: "Comprehensive secure coding instructions for all languages and frameworks, based on OWASP Top 10 and industry best practices."
---

# Secure Coding and OWASP Guidelines

## Instructions

All generated, reviewed, or refactored code must be secure by default. Security-first mindset. When in doubt, choose the more secure option and explain why.

### 1. A01: Broken Access Control & A10: SSRF

- **Enforce Principle of Least Privilege**: deny by default, grant only explicit allow rules.
- **Validate all incoming URLs for SSRF**: treat user-provided URLs as untrusted; use strict allow-list validation on host, port, and path.
- **Prevent path traversal**: sanitize file path inputs; use secure path-building APIs.

### 2. A02: Cryptographic Failures

- Use strong, modern algorithms (Argon2/bcrypt for hashing; AES-256 for data at rest).
- Default to HTTPS for all network requests.
- Never hardcode secrets — read from environment variables or a secrets manager.

### 3. A03: Injection

- No raw SQL/SOQL built from string concatenation — use parameterized queries or bind variables.
- Sanitize command-line input to prevent shell injection.
- Prefer `.textContent` over `.innerHTML`; sanitize with DOMPurify when `innerHTML` is unavoidable.

### 4. A05/A06: Security Misconfiguration & Vulnerable Components

- Disable verbose errors and debug features in production.
- Set security headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`).
- Keep dependencies up to date; run `npm audit` / equivalent for new libraries.

### 5. A07: Identification & Authentication Failures

- Generate a new session ID on login to prevent fixation.
- Set cookies with `HttpOnly`, `Secure`, and `SameSite=Strict`.
- Add rate limiting and lockout to auth and password reset flows.

### 6. A08: Software and Data Integrity Failures

- Never deserialize untrusted data without strict type checking.

## Language & Terminology

Never use biased terminology (`whitelist`, `blacklist`, `slave`, etc.) in code, comments, documentation, or metadata — use `allowlist`, `denylist`/`blocklist`, `replica`/`secondary`/`worker` instead.

## Agent Protocol

Use `vscode_askQuestions` for any clarification needed mid-task rather than stopping. Delegate heavy analysis to subagents and instruct them to return only key findings.
