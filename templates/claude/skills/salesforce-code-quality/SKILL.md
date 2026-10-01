---
name: salesforce-code-quality
description: 'Scan a Salesforce DX codebase for code quality issues. Use when the user asks to find unused or deprecated metadata (classes, LWC, Aura, flows, objects, fields), run an IDOR security scan, or generate a class inventory CSV mapping classes to their test classes. Works on the local force-app directory without needing org access.'
---

# Salesforce Code Quality

## Purpose

Three static-analysis scripts that work on the local `force-app/` directory:

1. **Deprecated / unused metadata scanner** — Find Apex classes, LWC/Aura bundles,
   flows, objects, and fields with zero textual references.
2. **IDOR vulnerability scanner** — Detect Insecure Direct Object Reference
   patterns, missing sharing models, SOQL injection risks, and more.
3. **Class inventory builder** — Create a CSV mapping every Apex class to its
   corresponding test class.

## Scripts

All scripts live under `.github/skills/salesforce-code-quality/scripts/`.

### deprecated_metadata.py

Static textual analysis that flags metadata with no references elsewhere in
`force-app/`. Results are _candidates_—review before removal.

```bash
# Default: Markdown report
python3 .github/skills/salesforce-code-quality/scripts/deprecated_metadata.py

# Full output (Markdown + JSON + CSV)
python3 .github/skills/salesforce-code-quality/scripts/deprecated_metadata.py \
  --force-app ./force-app \
  --output code-quality/unused_report.md \
  --json code-quality/unused_report.json \
  --csv code-quality/unused_report.csv

# Override exclusion prefixes
python3 .github/skills/salesforce-code-quality/scripts/deprecated_metadata.py \
  --exclude-prefix B25_,Temp_,Old_
```

**Categories scanned:** Apex classes, LWC bundles, Aura bundles, Flows, Custom
objects, Custom fields.

**Default exclusion prefixes:** `tmp_`, `z_`, `arch_`, `backup_`, `deprecated_`,
`old_` (case-insensitive). Test classes (`*Test`, `Test*`, `*Mock`, etc.) are
auto-excluded.

### idor_scanner.py

Regex-based security scanner for Salesforce Apex code. Detects 17 vulnerability
patterns across four severity levels.

```bash
# Scan all files, output CSV
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py

# Scan specific files, terminal output
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py \
  --files force-app/main/default/classes/Acme_AccountService.cls \
  --output terminal

# Both CSV and terminal
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py --output both
```

**Severity levels & pattern highlights:**

| Severity | Examples                                                                    |
| -------- | --------------------------------------------------------------------------- |
| Critical | Missing sharing model, SOQL injection, IDOR (no re-query), userId parameter |
| High     | DML in loop, SOQL in loop, hardcoded IDs, HTTP callout without validation   |
| Medium   | Missing recursion guard, inconsistent error handling, outdated API version  |
| Low      | `System.debug()` usage, commented-out code                                  |

**Output:** `idor_violations.csv` (or custom path via `--output-file`).

### create_classes_csv.py

Scans `force-app/main/default/classes/` and builds a CSV with two columns:

- `ClassName` — every non-test Apex class
- `TestClassName` — the matching test class (if one exists)

```bash
python3 .github/skills/salesforce-code-quality/scripts/create_classes_csv.py
```

**Output:** `code-quality/classes.csv`

Detection logic: name patterns (`*Test`, `Test*`, `*Mock`) and `@isTest`
annotation. This CSV is consumed by the **apex-test-analysis** skill's
`process_apex_tests.py`.

## Typical Workflow

```bash
# 1. Build the class inventory
python3 .github/skills/salesforce-code-quality/scripts/create_classes_csv.py

# 2. Find unused metadata
python3 .github/skills/salesforce-code-quality/scripts/deprecated_metadata.py \
  --csv code-quality/unused_report.csv

# 3. Run IDOR security scan
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py --output both

# 4. Review outputs in code-quality/ and idor_violations.csv
```

## Interaction Protocol

- **User input**: Use `vscode_askQuestions` for any confirmation or clarification needed mid-workflow. Never stop and wait for a follow-up prompt.
- **Session end**: Confirm with the user via `vscode_askQuestions` before ending the session.
- **Subagents**: Offload heavy analysis to subagents. Tell them: *"Return only key findings. Be concise — no verbose explanations, no raw data."*
