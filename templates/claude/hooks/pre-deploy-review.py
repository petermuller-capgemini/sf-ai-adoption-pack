#!/usr/bin/env python3
"""Pre-deploy quality gate hook — runs before every `sf project deploy start` Bash call.

Reads the tool call JSON from stdin, short-circuits for non-deploy calls,
then runs three automated quality gates:
  1. Merge-conflict-unsafe comment check (grep)
  2. IDOR security scanner (if present under .github/skills/)
  3. sf code-analyzer static analysis

Outputs Claude Code PreToolUse JSON (hookSpecificOutput).
  permissionDecision "deny"  — blocks deploy, Claude sees findings as context
  permissionDecision "allow" — gates passed, deploy proceeds with a note
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"timed out after {timeout}s"


def output_decision(decision: str, reason: str = "", context: str = "") -> None:
    payload: dict = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
        }
    }
    if reason:
        payload["hookSpecificOutput"]["permissionDecisionReason"] = reason
    if context:
        payload["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(payload))


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    if tool_name != "Bash" or "sf project deploy start" not in tool_input.get("command", ""):
        sys.exit(0)

    _, raw, _ = run(["git", "diff", "--name-only", "--cached"])
    staged = [f for f in raw.strip().splitlines() if f.startswith("force-app/")]

    if not staged:
        output_decision("allow", context="No staged force-app files — quality gates skipped.")
        sys.exit(0)

    apex_files = [f for f in staged if f.endswith(".cls") and not f.endswith("-meta.xml")]
    lwc_files = [f for f in staged if "/lwc/" in f and f.endswith(".js")]

    findings: list[str] = []
    notes: list[str] = []

    # Gate 1: merge-conflict-unsafe comments (breaks some CI/CD auto-resolution tools)
    _, grep_out, _ = run([
        "grep", "-rn",
        r"//.*=\{3,\}\|//.*>\{3,\}\|//.*<\{3,\}",
        "force-app/main/default/",
    ])
    if grep_out.strip():
        findings.append(
            "Merge-conflict-unsafe comments found (replace with // -- SECTION --):\n"
            + grep_out.strip()
        )
    else:
        notes.append("Merge-conflict comment check: clean")

    # Gate 2: IDOR security scanner
    idor_script = Path(".github/skills/salesforce-code-quality/scripts/idor_scanner.py")
    if apex_files and idor_script.exists():
        rc, idor_out, idor_err = run(
            ["python3", str(idor_script), "--files"] + apex_files + ["--output", "terminal"],
            timeout=30,
        )
        if rc != 0 or "CRITICAL" in idor_out.upper():
            findings.append(f"IDOR scanner — critical findings:\n{idor_out.strip() or idor_err.strip()}")
        else:
            snippet = (" — " + idor_out.strip()[:120]) if idor_out.strip() else ""
            notes.append(f"IDOR scanner: clean{snippet}")
    elif apex_files:
        notes.append("IDOR scanner: skipped (script not found)")
    else:
        notes.append("IDOR scanner: skipped (no Apex files staged)")

    # Gate 3: sf code-analyzer static analysis
    analysis_targets = apex_files + lwc_files
    if analysis_targets:
        target_args: list[str] = []
        for f in analysis_targets:
            target_args += ["--target", f]
        rc, analyzer_out, analyzer_err = run(
            ["sf", "code-analyzer", "run"] + target_args + ["--view", "detail"],
            timeout=90,
        )
        if rc != 0 and ("CRITICAL" in analyzer_out.upper() or "HIGH" in analyzer_out.upper()):
            findings.append(f"Code analyzer — findings:\n{analyzer_out.strip() or analyzer_err.strip()}")
        else:
            notes.append("Code analyzer: no blocking findings")
    else:
        notes.append("Code analyzer: skipped (no Apex/LWC files staged)")

    if findings:
        output_decision(
            "deny",
            reason="Pre-deploy quality gates found blocking issues.",
            context="\n\n".join(findings),
        )
    else:
        output_decision("allow", context="Quality gates passed:\n" + "\n".join(notes))


if __name__ == "__main__":
    main()
