---
name: code-analysis-compare
description: >
    Compare two Salesforce sfdx-scanner code-analysis CSV files to identify new violations
    (regressions introduced in the newer scan) and fixed violations (issues resolved since
    the older scan). Use when the user provides two code-analysis CSV files named with the
    pattern *-YYYYMMDD-HHMMSS.csv and wants to diff the results, track quality trends, or
    clean up after reviewing the comparison. Handles finding newer/older file automatically
    from the embedded date in the filename.
---

# Code Analysis Compare

## Overview

Compare two sfdx-scanner CSV reports to surface **new violations** (regressions) and
**fixed violations** (improvements) between two scan runs. A bundled Python script does
the heavy lifting — the agent's role is to invoke it, interpret the output, and present a
clear summary to the developer.

## CSV Format

The CSV files use the sfdx-scanner output format with these columns:

| Column        | Description                                      |
| ------------- | ------------------------------------------------ |
| `rule`        | Rule name (e.g. `AvoidOldSalesforceApiVersions`) |
| `engine`      | Scanner engine (e.g. `regex`, `pmd`)             |
| `severity`    | 1=Critical 2=High 3=Medium 4=Low 5=Info          |
| `tags`        | Comma-separated tag list                         |
| `file`        | Relative path to the file with the violation     |
| `startLine`   | Line number                                      |
| `startColumn` | Column number                                    |
| `endLine`     | End line                                         |
| `endColumn`   | End column                                       |
| `message`     | Human-readable violation description             |
| `resources`   | Optional link(s)                                 |

**Violation identity key**: `rule` + `file` + `startLine` + `startColumn`

## Workflow

1. **Locate files** — confirm the two CSV paths the user provided.
2. **Run the script** — execute `scripts/compare_code_analysis.py`:
    ```bash
    python3 .github/skills/code-analysis-compare/scripts/compare_code_analysis.py <file1.csv> <file2.csv>
    ```
    The script auto-detects which file is older using the date embedded in the filename
    (`*-YYYYMMDD-HHMMSS.csv`), falling back to file modification time.
3. **Summarise output** — present the counts and highlight any new violations by rule and severity.
4. **Clean up** (if requested) — delete the CSV files after the comparison is done.

## Script Exit Codes

| Code | Meaning                                     |
| ---- | -------------------------------------------- |
| `0`  | No new violations — no regressions          |
| `1`  | New violations detected — regressions exist |

Use exit code `1` in CI pipelines to block merges when regressions are introduced.

## Interaction Protocol

- **User input**: Use `vscode_askQuestions` for any confirmation or clarification needed mid-workflow. Never stop and wait for a follow-up prompt.
- **Session end**: Confirm with the user via `vscode_askQuestions` before ending the session.
- **Subagents**: Offload heavy analysis to subagents. Tell them: *"Return only key findings. Be concise — no verbose explanations, no raw data."*
