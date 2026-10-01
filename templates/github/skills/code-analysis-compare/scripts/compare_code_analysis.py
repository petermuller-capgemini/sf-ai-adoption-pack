#!/usr/bin/env python3
"""
compare_code_analysis.py
Compare two Salesforce code-analysis CSV files produced by sfdx-scanner
and report new violations (regressions) and fixed violations (improvements).

Usage:
    python3 compare_code_analysis.py <older.csv> <newer.csv>

The date is parsed from the filename using the pattern:
    <prefix>-YYYYMMDD-HHMMSS.csv

Violation identity key: rule + file + startLine + startColumn
"""

import csv
import sys
import os
import re
from datetime import datetime
from collections import defaultdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATE_PATTERN = re.compile(r"(\d{8})-(\d{6})")


def parse_date_from_filename(path: str) -> datetime | None:
    """Extract datetime from filename if it matches *-YYYYMMDD-HHMMSS.csv."""
    name = os.path.basename(path)
    m = DATE_PATTERN.search(name)
    if m:
        return datetime.strptime(f"{m.group(1)}{m.group(2)}", "%Y%m%d%H%M%S")
    return None


def load_violations(path: str) -> dict[tuple, dict]:
    """
    Load CSV and return a dict keyed by (rule, file, startLine, startColumn).
    Each value is the full row as a dict.
    """
    violations: dict[tuple, dict] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (
                row.get("rule", ""),
                row.get("file", ""),
                row.get("startLine", ""),
                row.get("startColumn", ""),
            )
            violations[key] = row
    return violations


def severity_label(severity: str) -> str:
    mapping = {"1": "Critical", "2": "High", "3": "Medium", "4": "Low", "5": "Info"}
    return mapping.get(str(severity).strip(), severity)


def print_section(title: str, rows: list[dict], label: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}  ({len(rows)} violations)")
    print("=" * 70)
    if not rows:
        print("  None")
        return

    # Group by rule for readability
    by_rule: dict[str, list[dict]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: (r.get("rule", ""), r.get("file", ""))):
        by_rule[row.get("rule", "unknown")].append(row)

    for rule, rule_rows in by_rule.items():
        sev = severity_label(rule_rows[0].get("severity", ""))
        print(f"\n  [{label}] Rule: {rule}  |  Severity: {sev}  |  Count: {len(rule_rows)}")
        for row in rule_rows:
            file_path = row.get("file", "")
            line = row.get("startLine", "?")
            msg = row.get("message", "")
            # Trim long paths for readability
            display_path = "/".join(file_path.replace("\\", "/").split("/")[-4:])
            print(f"    • {display_path}:{line}  —  {msg[:120]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: compare_code_analysis.py <file1.csv> <file2.csv>")
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]

    for p in (path_a, path_b):
        if not os.path.isfile(p):
            print(f"Error: file not found: {p}")
            sys.exit(1)

    # Determine which is older vs newer by embedded date, fallback to mtime
    date_a = parse_date_from_filename(path_a) or datetime.fromtimestamp(os.path.getmtime(path_a))
    date_b = parse_date_from_filename(path_b) or datetime.fromtimestamp(os.path.getmtime(path_b))

    if date_a <= date_b:
        older_path, newer_path = path_a, path_b
        older_date, newer_date = date_a, date_b
    else:
        older_path, newer_path = path_b, path_a
        older_date, newer_date = date_b, date_a

    print(f"\nOlder scan : {os.path.basename(older_path)}  ({older_date.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"Newer scan : {os.path.basename(newer_path)}  ({newer_date.strftime('%Y-%m-%d %H:%M:%S')})")

    older = load_violations(older_path)
    newer = load_violations(newer_path)

    older_keys = set(older.keys())
    newer_keys = set(newer.keys())

    new_violations  = [newer[k] for k in newer_keys - older_keys]  # regressions
    fixed_violations = [older[k] for k in older_keys - newer_keys]  # improvements
    unchanged = older_keys & newer_keys

    # Summary
    print(f"\n{'─' * 70}")
    print(f"  SUMMARY")
    print(f"{'─' * 70}")
    print(f"  Violations in older scan : {len(older_keys)}")
    print(f"  Violations in newer scan : {len(newer_keys)}")
    print(f"  Unchanged                : {len(unchanged)}")
    print(f"  NEW  (regressions)       : {len(new_violations)}")
    print(f"  FIXED (improvements)     : {len(fixed_violations)}")
    net = len(newer_keys) - len(older_keys)
    trend = f"+{net}" if net > 0 else str(net)
    print(f"  Net change               : {trend}")

    print_section("NEW VIOLATIONS (regressions — appeared in newer scan)", new_violations, "NEW")
    print_section("FIXED VIOLATIONS (resolved — gone from newer scan)", fixed_violations, "FIXED")

    print(f"\n{'=' * 70}\n")

    # Exit code signals whether regressions exist (useful for CI)
    sys.exit(1 if new_violations else 0)


if __name__ == "__main__":
    main()
