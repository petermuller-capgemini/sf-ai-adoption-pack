---
name: salesforce-org-compare
description: 'Compare Salesforce data between two orgs. Use when the user asks to compare records, products, pricebooks, or any SObject data across two Salesforce orgs. Identifies records unique to each org and field-level differences. Supports custom SOQL queries, configurable key fields, and optional pricebook entry comparison.'
---

# Salesforce Org Compare

## Purpose

Query the same SObject from two Salesforce orgs via the `sf` CLI and produce a
detailed comparison report showing:

- Records unique to each org
- Records present in both but with field-level differences
- Optional pricebook entry comparison

## Scripts

All scripts live under `.github/skills/salesforce-org-compare/scripts/`.

### compare_products.py

Despite the filename, this script can compare **any SObject** between two orgs
when you supply a `--query` argument.

```bash
# Default: Compare active Product2 records
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2

# Include inactive records
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --include-inactive

# Compare any SObject with a custom SOQL query
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 \
  --query "SELECT Name, CurrencyIsoCode, IsActive FROM Pricebook2"

# Use a different key field for matching records
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 \
  --query "SELECT Name, IsActive FROM Pricebook2" \
  --key-field Name

# Ignore additional fields in the diff
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 \
  --ignore-fields Id CreatedDate LastModifiedDate Description

# Include pricebook entry comparison (Product2 only, slower)
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --include-pricing

# Custom output directory
python3 .github/skills/salesforce-org-compare/scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 \
  --output-dir comparison_results
```

**Parameters:**

| Flag                 | Default                                 | Description                 |
| -------------------- | ---------------------------------------- | --------------------------- |
| `--org1`             | _(required)_                            | First org alias             |
| `--org2`             | _(required)_                            | Second org alias            |
| `--query`            | Default Product2 query                  | Custom SOQL query           |
| `--key-field`        | `ProductCode` (fallback `Id`)           | Field used to match records |
| `--ignore-fields`    | `Id`, `CreatedDate`, `LastModifiedDate` | Fields to skip during diff  |
| `--include-inactive` | `false`                                  | Include inactive records    |
| `--include-pricing`  | `false`                                  | Also compare PricebookEntry |
| `--output-dir`       | `product_comparison/`                   | Output directory            |

**Output files:**

- `comparison_summary.txt` — Human-readable report
- `comparison_details.csv` — Spreadsheet with per-field diffs
- `pricing_comparison.json` — (only with `--include-pricing`)

**Prerequisites:** Salesforce CLI (`sf`) authenticated to both orgs.

## Interaction Protocol

- **User input**: Use `vscode_askQuestions` for any confirmation or clarification needed mid-workflow. Never stop and wait for a follow-up prompt.
- **Session end**: Confirm with the user via `vscode_askQuestions` before ending the session.
- **Subagents**: Offload heavy analysis to subagents. Tell them: *"Return only key findings. Be concise — no verbose explanations, no raw data."*
