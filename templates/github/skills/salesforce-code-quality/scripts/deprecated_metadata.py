#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
deprecated_metadata.py

Scans a Salesforce DX (SFDX) codebase in ../force-app to identify *possibly unused* metadata:
- Apex classes
- LWC component bundles
- Aura component bundles
- Flows
- Custom objects and fields (flags fields not referenced as "Object__c.Field__c")

Exports:
- Markdown summary (table per category)
- Optional JSON
- Optional CSV (flat list with columns: category, name, path, references_found, note)

IMPORTANT:
- This is a best-effort static scanner based on textual references.
- Results are "candidates" only. Review before removal.
- Dynamic references, metadata-driven usage, and managed packages will not be reliably detected.

Usage:
  python3 scripts/deprecated_metadata.py \
      --force-app ./force-app \
      --output code-quality/unused_report.md \
      --json code-quality/unused_report.json \
      --csv code-quality/unused_report.csv \
      --exclude-prefix B25_,Temp_,Old_

Author: Peter Muller
"""

from __future__ import annotations
import argparse
import os
import re
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple, Iterable, Optional
from collections import defaultdict

# ----------------------------
# Configuration (editable)
# ----------------------------

# Default exclusion prefixes for metadata names (case-insensitive). You can pass CLI overrides.
DEFAULT_EXCLUDE_PREFIXES: List[str] = [
    "tmp_", "z_", "arch_", "backup_", "deprecated_", "old_"
]

# Ignore common test/mock class name patterns
IGNORE_TEST_CLASSES = True
TEST_CLASS_PATTERNS = [
    r".*Test$", r"^Test.*", r".*Tests$", r".*Mock$", r".*Stub$", r".*Fake$"
]

# Directories we won't scan for references.
IGNORE_DIR_NAMES = {
    ".sfdx", ".git", ".github", "node_modules", "scripts", ".vscode", ".idea"
}

# File extensions we will scan contents of for references.
SCANNED_EXTENSIONS = {
    ".cls", ".trigger", ".page", ".component", ".cmp", ".app", ".evt", ".intf",
    ".xml", ".js", ".ts", ".html", ".css", ".json", ".resource", ".md",
    ".AuraDefinitionBundle-meta.xml", ".labels-meta.xml"
}

# ----------------------------
# Helpers
# ----------------------------

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def kebab_to_pascal(name: str) -> str:
    # hello-world -> HelloWorld; also upgrades camelCase -> PascalCase
    if "-" in name:
        parts = name.split("-")
        return "".join(p.capitalize() for p in parts if p)
    return name[:1].upper() + name[1:]

def any_to_kebab(name: str) -> str:
    # CamelCase/PascalCase -> kebab-case; kebab remains kebab
    if "-" in name:
        return name.lower()
    # Insert hyphens before capitals (excluding the first char)
    kebab = re.sub(r"(?<!^)([A-Z])", r"-\1", name).lower()
    return kebab

def any_to_camel(name: str) -> str:
    # kebab-case -> camelCase; PascalCase -> camelCase; camelCase -> camelCase
    if "-" in name:
        parts = [p for p in name.split("-") if p]
        if not parts:
            return ""
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])
    # No hyphens: lower first char
    return name[:1].lower() + name[1:]

def starts_with_any(name: str, prefixes: Iterable[str]) -> bool:
    low = name.lower()
    for p in prefixes:
        if low.startswith(p.lower()):
            return True
    return False

def compile_patterns(patterns: Iterable[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]

def matches_any_regex(name: str, regexes: List[re.Pattern]) -> bool:
    return any(rx.match(name) for rx in regexes)

def safe_regex_escape(name: str) -> str:
    return re.escape(name)

def list_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIR_NAMES]
        for fname in filenames:
            files.append(Path(dirpath) / fname)
    return files

def looks_like_sfdx_force_app(force_app: Path) -> bool:
    # heuristic: should contain main/default with typical dirs
    main_default = force_app / "main" / "default"
    return main_default.exists()

# ----------------------------
# Declarations Discovery
# ----------------------------

class Declarations:
    def __init__(self):
        self.apex_classes: Dict[str, Path] = {}   # ClassName -> path
        self.aura_bundles: Dict[str, Path] = {}   # BundleName -> bundle dir
        self.lwc_bundles: Dict[str, Path] = {}    # bundle (folder) -> bundle dir
        self.flows: Dict[str, Path] = {}          # FlowApiName -> file
        self.objects: Dict[str, Path] = {}        # ObjectApiName -> object dir or object meta file
        self.fields: Dict[Tuple[str, str], Path] = {}  # (ObjectApiName, FieldApiName) -> field file

def gather_declarations(force_app: Path) -> Declarations:
    decl = Declarations()
    main_default = force_app / "main" / "default"

    # Apex classes
    classes_dir = main_default / "classes"
    if classes_dir.exists():
        for p in classes_dir.glob("*.cls"):
            class_name = p.stem
            decl.apex_classes[class_name] = p

    # Aura bundles
    aura_dir = main_default / "aura"
    if aura_dir.exists():
        for b in aura_dir.iterdir():
            if b.is_dir() and any(x.suffix == ".cmp" for x in b.iterdir()):
                decl.aura_bundles[b.name] = b

    # LWC bundles
    lwc_dir = main_default / "lwc"
    if lwc_dir.exists():
        for b in lwc_dir.iterdir():
            if b.is_dir():
                decl.lwc_bundles[b.name] = b

    # Flows
    flows_dir = main_default / "flows"
    if flows_dir.exists():
        for p in flows_dir.glob("*.flow-meta.xml"):
            flow_name = p.stem  # file name before .flow-meta.xml
            decl.flows[flow_name] = p

    # Objects & Fields
    objects_dir = main_default / "objects"
    if objects_dir.exists():
        for obj in objects_dir.iterdir():
            if not obj.is_dir():
                continue
            object_name = obj.name  # e.g., Account or Custom__c
            decl.objects[object_name] = obj
            fields_dir = obj / "fields"
            if fields_dir.exists():
                for f in fields_dir.glob("*.field-meta.xml"):
                    field_name = f.stem  # e.g., MyField__c
                    decl.fields[(object_name, field_name)] = f

    return decl

# ----------------------------
# Content Index
# ----------------------------

class ContentIndex:
    def __init__(self):
        self.files: List[Path] = []
        self.texts: Dict[Path, str] = {}
        self.lower_texts: Dict[Path, str] = {}

    def build(self, root: Path) -> None:
        for f in list_files(root):
            if f.suffix in SCANNED_EXTENSIONS or f.name.endswith("-meta.xml"):
                txt = read_text(f)
                self.files.append(f)
                self.texts[f] = txt
                self.lower_texts[f] = txt.lower()

    def search_exact(self, needle: str, ignore_files: Optional[Set[Path]] = None, case_sensitive: bool = True) -> int:
        if ignore_files is None:
            ignore_files = set()
        count = 0
        if case_sensitive:
            for f in self.files:
                if f in ignore_files:
                    continue
                if needle in self.texts.get(f, ""):
                    count += 1
        else:
            ln = needle.lower()
            for f in self.files:
                if f in ignore_files:
                    continue
                if ln in self.lower_texts.get(f, ""):
                    count += 1
        return count

    def search_regex(self, pattern: re.Pattern, ignore_files: Optional[Set[Path]] = None) -> int:
        if ignore_files is None:
            ignore_files = set()
        cnt = 0
        for f in self.files:
            if f in ignore_files:
                continue
            txt = self.texts.get(f, "")
            if pattern.search(txt):
                cnt += 1
        return cnt

# ----------------------------
# Reference Heuristics
# ----------------------------

def is_excluded(name: str, exclude_prefixes: Iterable[str]) -> bool:
    return starts_with_any(name, exclude_prefixes)

def is_test_class(name: str) -> bool:
    if not IGNORE_TEST_CLASSES:
        return False
    rx = compile_patterns(TEST_CLASS_PATTERNS)
    return matches_any_regex(name, rx)

def find_apex_references(name: str, idx: ContentIndex, self_file: Optional[Path]) -> int:
    # Word boundary to reduce false positives
    ignore = {self_file} if self_file else set()
    pattern = re.compile(r"\b" + safe_regex_escape(name) + r"\b")
    return idx.search_regex(pattern, ignore_files=ignore)

def find_lwc_references(bundle: str, idx: ContentIndex, bundle_dir: Path) -> int:
    """
    Detects LWC usage via:
      - LWC HTML templates: <c-my-lwc ...> (kebab-case)
      - JS/TS imports: from 'c/myLwc' (camelCase)
      - Aura usage: <c:myLwc ...> (camelCase) or <c:MyLwc ...> (PascalCase)
    """
    ignore = set(bundle_dir.rglob("*"))
    kebab = any_to_kebab(bundle)
    camel = any_to_camel(bundle)
    pascal = kebab_to_pascal(bundle)

    # 1) LWC template custom element: <c-{kebab}
    c1 = idx.search_exact(f"<c-{kebab}", ignore_files=ignore, case_sensitive=False)

    # 2) Imports from 'c/{camel}' in JS/TS
    c2 = idx.search_exact(f"c/{camel}", ignore_files=ignore, case_sensitive=True)

    # 3) Aura inclusion or dependency: c:{camel} and c:{pascal}
    c3 = idx.search_exact(f"c:{camel}", ignore_files=ignore, case_sensitive=False)
    c4 = idx.search_exact(f"c:{pascal}", ignore_files=ignore, case_sensitive=False)

    return c1 + c2 + c3 + c4
def find_aura_references(bundle: str, idx: ContentIndex, bundle_dir: Path) -> int:
    """
    Detects Aura usage via tags like:
      - <c:BundleName ...> (as-is)
      - <c:BundleName ...> where BundleName is PascalCase
      - <c:bundleName ...> camelCase
      - <c:bundle-name ...> kebab-case (rare, but included)
    """
    ignore = set(bundle_dir.rglob("*"))
    as_is = bundle
    pascal = kebab_to_pascal(bundle)
    camel = any_to_camel(bundle)
    kebab = any_to_kebab(bundle)

    c1 = idx.search_exact(f"<c:{as_is}", ignore_files=ignore, case_sensitive=False)
    c2 = idx.search_exact(f"<c:{pascal}", ignore_files=ignore, case_sensitive=False)
    c3 = idx.search_exact(f"<c:{camel}", ignore_files=ignore, case_sensitive=False)
    c4 = idx.search_exact(f"<c:{kebab}", ignore_files=ignore, case_sensitive=False)

    return c1 + c2 + c3 + c4

def find_flow_references(flow_name: str, idx: ContentIndex, flow_file: Path) -> int:
    ignore = {flow_file}
    # LWC lightning-flow: flow-api-name="Flow_Name"
    c1 = idx.search_exact(f'flow-api-name="{flow_name}"', ignore_files=ignore, case_sensitive=True)
    # Apex: Flow.Interview.Flow_Name or start('Flow_Name')
    c2 = idx.search_exact(f"Flow.Interview.{flow_name}", ignore_files=ignore, case_sensitive=True)
    c3 = idx.search_exact(f"start('{flow_name}')", ignore_files=ignore, case_sensitive=True)
    c4 = idx.search_exact(f'start("{flow_name}")', ignore_files=ignore, case_sensitive=True)
    return c1 + c2 + c3 + c4

def find_field_references(object_name: str, field_name: str, idx: ContentIndex, field_file: Path) -> int:
    ignore = {field_file}
    dotted = f"{object_name}.{field_name}"
    c1 = idx.search_exact(dotted, ignore_files=ignore, case_sensitive=True)
    return c1
def find_object_references(object_name: str, idx: ContentIndex, object_path: Path) -> int:
    ignore = set(object_path.rglob("*")) if object_path.is_dir() else {object_path}
    return idx.search_exact(object_name, ignore_files=ignore, case_sensitive=True)

# ----------------------------
# Report Model
# ----------------------------

def make_row(category: str, name: str, path: Path, references: int, note: str = "") -> Dict[str, str]:
    return {
        "category": category,
        "name": name,
        "path": str(path),
        "references_found": str(references),
        "note": note
    }

# ----------------------------
# Main scanning
# ----------------------------

def scan(force_app: Path, exclude_prefixes: List[str]) -> Dict[str, List[Dict[str, str]]]:
    decl = gather_declarations(force_app)
    idx = ContentIndex()
    idx.build(force_app)

    results: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    # Apex classes
    for cls, p in sorted(decl.apex_classes.items()):
        if is_excluded(cls, exclude_prefixes) or is_test_class(cls):
            continue
        refs = find_apex_references(cls, idx, self_file=p)
        if refs == 0:
            results["apex_classes"].append(
                make_row("apex_class", cls, p, refs, "No textual references found")
            )

    # LWC bundles
    for bundle, bdir in sorted(decl.lwc_bundles.items()):
        if is_excluded(bundle, exclude_prefixes):
            continue
        refs = find_lwc_references(bundle, idx, bundle_dir=bdir)
        if refs == 0:
            results["lwc_bundles"].append(
                make_row("lwc_bundle", bundle, bdir, refs, "No textual references found")
            )

    # Aura bundles
    for bundle, bdir in sorted(decl.aura_bundles.items()):
        if is_excluded(bundle, exclude_prefixes):
            continue
        refs = find_aura_references(bundle, idx, bundle_dir=bdir)
        if refs == 0:
            results["aura_bundles"].append(
                make_row("aura_bundle", bundle, bdir, refs, "No textual references found")
            )

    # Flows
    for flow, fpath in sorted(decl.flows.items()):
        if is_excluded(flow, exclude_prefixes):
            continue
        refs = find_flow_references(flow, idx, flow_file=fpath)
        if refs == 0:
            results["flows"].append(
                make_row("flow", flow, fpath, refs, "No textual references found")
            )

    # Objects
    for obj, opath in sorted(decl.objects.items()):
        if is_excluded(obj, exclude_prefixes):
            continue
        refs = find_object_references(obj, idx, object_path=opath)
        if refs == 0:
            results["objects"].append(
                make_row("object", obj, opath, refs, "No textual references found")
            )

    # Fields
    for (obj, fld), fpath in sorted(decl.fields.items()):
        if is_excluded(fld, exclude_prefixes) or is_excluded(obj, exclude_prefixes):
            continue
        refs = find_field_references(obj, fld, idx, field_file=fpath)
        if refs == 0:
            results["fields"].append(
                make_row("field", f"{obj}.{fld}", fpath, refs, "No textual references found (exact 'Object.Field')")
            )

    return results

# ----------------------------
# Writers: Markdown / JSON / CSV
# ----------------------------

def write_markdown(report: Dict[str, List[Dict[str, str]]], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# Possible Unused Salesforce Metadata Report\n")
    total = sum(len(v) for v in report.values())
    lines.append(f"**Total candidates:** {total}\n")
    lines.append("> ⚠️ This is a static textual analysis. Review each item before removal.\n")

    for key in ["apex_classes", "lwc_bundles", "aura_bundles", "flows", "objects", "fields"]:
        rows = report.get(key, [])
        if not rows:
            continue
        title = key.replace("_", " ").title()
        lines.append(f"\n## {title} ({len(rows)})\n")
        lines.append("| Name | Path | Notes |")
        lines.append("|------|------|-------|")
        for r in rows:
            name = r["name"]
            path = r["path"]
            note = r.get("note", "")
            lines.append(f"| `{name}` | `{path}` | {note} |")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

def write_json(report: Dict[str, List[Dict[str, str]]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

def write_csv(report: Dict[str, List[Dict[str, str]]], out_path: Path) -> None:
    """
    Writes a flat CSV with columns:
    category,name,path,references_found,note
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["category", "name", "path", "references_found", "note"]
    ordered_sections = ["apex_classes", "lwc_bundles", "aura_bundles", "flows", "objects", "fields"]
    rows: List[Dict[str, str]] = []
    for section in ordered_sections:
        rows.extend(report.get(section, []))
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "category": r.get("category", ""),
                "name": r.get("name", ""),
                "path": r.get("path", ""),
                "references_found": r.get("references_found", ""),
                "note": r.get("note", ""),
            })

# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    default_force_app = (Path(__file__).resolve().parent.parent / "force-app").as_posix()
    parser = argparse.ArgumentParser(description="Scan SFDX force-app for possibly unused metadata.")
    parser.add_argument("--force-app", type=str, default=default_force_app,
                        help="Path to the force-app directory (default: ../force-app relative to this script).")
    parser.add_argument("--output", type=str, default="scripts/unused_report.md",
                        help="Path to write Markdown report (default: scripts/unused_report.md).")
    parser.add_argument("--json", type=str, default="",
                        help="Optional path to write JSON report.")
    parser.add_argument("--csv", type=str, default="",
                        help="Optional path to write CSV report.")
    parser.add_argument("--exclude-prefix", type=str, default="",
                        help="Comma-separated prefixes to exclude from search (case-insensitive).")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    force_app = Path(args.force_app).resolve()
    if not force_app.exists():
        print(f"[ERROR] force-app path not found: {force_app}", file=sys.stderr)
        return 2
    if not looks_like_sfdx_force_app(force_app):
        print(f"[WARN] {force_app} does not look like a typical SFDX 'force-app/main/default' structure.", file=sys.stderr)

    exclude_prefixes = DEFAULT_EXCLUDE_PREFIXES.copy()
    if args.exclude_prefix:
        extra = [p.strip() for p in args.exclude_prefix.split(",") if p.strip()]
        exclude_prefixes = extra  # override fully with CLI value

    print(f"[INFO] Scanning: {force_app}")
    print(f"[INFO] Exclusion prefixes: {exclude_prefixes}")

    report = scan(force_app, exclude_prefixes)

    md_path = Path(args.output).resolve()
    write_markdown(report, md_path)
    print(f"[INFO] Markdown report written to: {md_path}")

    if args.json:
        json_path = Path(args.json).resolve()
        write_json(report, json_path)
        print(f"[INFO] JSON report written to: {json_path}")

    if args.csv:
        csv_path = Path(args.csv).resolve()
        write_csv(report, csv_path)
        print(f"[INFO] CSV report written to: {csv_path}")

    total = sum(len(v) for v in report.values())
    print(f"[DONE] Candidates found: {total}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
