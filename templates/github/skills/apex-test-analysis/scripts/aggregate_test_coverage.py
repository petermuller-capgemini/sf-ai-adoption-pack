#!/usr/bin/env python3
"""
Aggregate test coverage and test result files into a CSV summary.

Usage:
  python3 scripts/aggregate_test_coverage.py --input-dir test_results --output-file test_results/coverage_summary.csv

The script is tolerant of several common Salesforce test-result / codecoverage JSON shapes and JUnit XML.

It creates one row per production class (from code coverage data) with these columns:
  class, total_lines, covered_lines, non_covered_lines, covered_percent,
  test_classes, total_test_time_seconds, passing_methods, failing_methods, error_messages

Notes / assumptions:
- Some coverage JSON outputs don't map which tests covered which classes. The script therefore
  aggregates test results globally and lists test classes seen; it does not assert per-test-to-class mapping.
- The parser is defensive: if fields are missing it will try multiple likely keys and continue.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from xml.etree import ElementTree as ET


def safe_load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load JSON {path}: {e}")
        return None


def parse_coverage_json(data):
    """Return list of coverage entries as dicts with keys: name, total_lines, covered_lines, not_covered"""
    if not data:
        return []

    results = []

    # Common shapes: top-level 'coverage' array
    candidates = []
    if isinstance(data, dict):
        if 'coverage' in data and isinstance(data['coverage'], list):
            candidates = data['coverage']
        # older sfdx format may have 'body' or other keys
        elif 'result' in data and isinstance(data['result'], list):
            candidates = data['result']
        elif 'records' in data and isinstance(data['records'], list):
            candidates = data['records']
        else:
            # maybe the file itself is an array
            if any(isinstance(v, list) for v in data.values()):
                # try to find the largest list
                largest = max((v for v in data.values() if isinstance(v, list)), key=len, default=None)
                if largest:
                    candidates = largest
    elif isinstance(data, list):
        candidates = data

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name') or entry.get('class') or entry.get('fullName') or entry.get('ApexClass') or entry.get('Id')

        # Try multiple conventions for line counts
        total = None
        covered = None
        not_covered = None
        explicit_percent = None

        # detect explicit coverage keys
        if 'totalCovered' in entry:
            try:
                covered = int(entry.get('totalCovered'))
            except Exception:
                covered = None
        if 'totalCoveredLines' in entry:
            try:
                covered = int(entry.get('totalCoveredLines'))
            except Exception:
                covered = covered
        if 'coveredPercent' in entry:
            try:
                explicit_percent = float(entry.get('coveredPercent'))
            except Exception:
                explicit_percent = explicit_percent
        if 'coveragePercent' in entry:
            try:
                explicit_percent = float(entry.get('coveragePercent'))
            except Exception:
                explicit_percent = explicit_percent
        if 'percentCovered' in entry:
            try:
                explicit_percent = float(entry.get('percentCovered'))
            except Exception:
                explicit_percent = explicit_percent

        # shape: numLocations and numLocationsNotCovered
        if total is None:
            nl = entry.get('numLocations') or entry.get('totalLines') or entry.get('lines')
            nnc = entry.get('numLocationsNotCovered') or entry.get('notCoveredLines') or entry.get('linesNotCovered')
            if nl is not None:
                try:
                    total = int(nl)
                except Exception:
                    total = None
            if nnc is not None:
                try:
                    not_covered = int(nnc)
                except Exception:
                    not_covered = None

        # shape: coveredLines, totalLines
        if total is None:
            tl = entry.get('totalLines') or entry.get('TotalLines')
            cl = entry.get('coveredLines') or entry.get('CoveredLines')
            if tl is not None:
                try:
                    total = int(tl)
                except Exception:
                    total = None
            if cl is not None:
                try:
                    covered = int(cl)
                except Exception:
                    covered = None

        # shape: locations and locationsNotCovered lists
        if total is None:
            locs = entry.get('locations') or entry.get('lines')
            if isinstance(locs, list):
                total = len(locs)

        if covered is None and total is not None and not_covered is not None:
            covered = total - not_covered

        # as fallback try to compute from 'coverage' key inside entry
        if covered is None and 'coverage' in entry:
            cov = entry.get('coverage')
            if isinstance(cov, dict):
                covered = cov.get('coveredLines')
                total = total or cov.get('totalLines')

        # final fallback: if we have integer fields directly
        if total is None:
            for k in ('total', 'Total', 'numLines'):
                if k in entry and isinstance(entry[k], int):
                    total = entry[k]

        # compute not_covered and covered
        if total is not None and covered is None and not_covered is not None:
            covered = total - not_covered

        if total is not None and covered is not None and not_covered is None:
            not_covered = total - covered

        # ensure ints or skip
        try:
            total_i = int(total) if total is not None else None
            covered_i = int(covered) if covered is not None else None
            not_covered_i = int(not_covered) if not_covered is not None else None
        except Exception:
            total_i = covered_i = not_covered_i = None

        # If there is an explicit percent, attach it to raw so it can be used later
        # normalize percent if it's given as fraction (0-1)
        if explicit_percent is not None:
            try:
                ep = float(explicit_percent)
                if 0.0 <= ep <= 1.0:
                    ep = ep * 100.0
                entry['_explicit_covered_percent'] = ep
            except Exception:
                entry['_explicit_covered_percent'] = explicit_percent

        if name is None:
            # try to infer name from 'Id' or similar
            name = entry.get('Id') or entry.get('id')

        results.append({
            'name': name,
            'total': total_i,
            'covered': covered_i,
            'not_covered': not_covered_i,
            'raw': entry,
        })

    return results


def parse_test_result_json(data):
    """Return list of test method dicts with keys: className, methodName, outcome, time, message"""
    out = []
    if not data:
        return out

    candidates = []
    if isinstance(data, dict):
        # common shape: 'tests' array
        if 'tests' in data and isinstance(data['tests'], list):
            candidates = data['tests']
        elif 'testResults' in data and isinstance(data['testResults'], list):
            candidates = data['testResults']
        elif 'runTestResult' in data and isinstance(data['runTestResult'], dict):
            r = data['runTestResult']
            if 'tests' in r and isinstance(r['tests'], list):
                candidates = r['tests']
        elif 'result' in data and isinstance(data['result'], dict) and 'tests' in data['result']:
            candidates = data['result']['tests']
        else:
            # try to find any list of dicts with 'methodName' keys
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict) and ('methodName' in v[0] or 'MethodName' in v[0] or 'outcome' in v[0]):
                    candidates = v
                    break
    elif isinstance(data, list):
        candidates = data

    for t in candidates:
        if not isinstance(t, dict):
            continue
        method = t.get('methodName') or t.get('MethodName') or t.get('name') or t.get('method')
        cls = None
        # sometimes nested under 'ApexClass'
        if 'ApexClass' in t and isinstance(t['ApexClass'], dict):
            cls = t['ApexClass'].get('Name') or t['ApexClass'].get('name')
        cls = cls or t.get('className') or t.get('class') or t.get('TestClassName') or t.get('className')
        outcome = t.get('outcome') or t.get('status') or t.get('result')
        time = t.get('time') or t.get('Time') or t.get('runTime') or t.get('duration')
        message = t.get('message') or t.get('error') or t.get('stackTrace') or t.get('failureMessage')

        # normalize
        try:
            time_f = float(time) if time is not None else None
        except Exception:
            time_f = None

        out.append({
            'class': cls,
            'method': method,
            'outcome': outcome,
            'time': time_f,
            'message': message,
            'raw': t,
        })

    return out


def parse_junit_xml(path):
    """Parse junit xml and return list of test dicts: class, method, time, outcome, message"""
    try:
        tree = ET.parse(path)
    except Exception as e:
        print(f"Warning: failed to parse xml {path}: {e}")
        return []

    root = tree.getroot()
    results = []
    # JUnit testcases
    for tc in root.findall('.//testcase'):
        classname = tc.get('classname') or tc.get('class')
        method = tc.get('name')
        time = tc.get('time')
        outcome = 'Pass'
        message = None
        # failures or errors
        f = tc.find('failure') or tc.find('error')
        if f is not None:
            outcome = 'Fail'
            message = (f.get('message') or f.text or '').strip()

        try:
            time_f = float(time) if time is not None else None
        except Exception:
            time_f = None

        results.append({'class': classname, 'method': method, 'time': time_f, 'outcome': outcome, 'message': message})

    return results


def aggregate(input_dir):
    coverage_map = {}
    test_methods = []
    test_classes = defaultdict(lambda: {'passing': [], 'failing': [], 'time': 0.0, 'errors': []})

    for fname in os.listdir(input_dir):
        path = os.path.join(input_dir, fname)
        if os.path.isdir(path):
            continue
        lower = fname.lower()
        if lower.endswith('.json'):
            data = safe_load_json(path)
            if data is None:
                continue
            # heuristic: if filename contains 'codecoverage' treat as coverage
            if 'codecoverage' in lower or 'coverage' in lower:
                entries = parse_coverage_json(data)
                for e in entries:
                    name = e['name'] or '(unknown)'
                    coverage_map[name] = {
                        'total': e['total'],
                        'covered': e['covered'],
                        'not_covered': e['not_covered']
                    }
            else:
                # treat as test result json
                methods = parse_test_result_json(data)
                for m in methods:
                    test_methods.append(m)
                    cls = m.get('class') or '(unknown)'
                    outcome = (m.get('outcome') or '').lower()
                    time = m.get('time') or 0.0
                    if outcome and 'pass' in outcome:
                        test_classes[cls]['passing'].append(m.get('method') or '')
                    else:
                        test_classes[cls]['failing'].append(m.get('method') or '')
                        if m.get('message'):
                            test_classes[cls]['errors'].append(str(m.get('message')))
                    try:
                        test_classes[cls]['time'] += float(time)
                    except Exception:
                        pass

        elif lower.endswith('.xml'):
            # try junit
            methods = parse_junit_xml(path)
            for m in methods:
                cls = m.get('class') or '(unknown)'
                outcome = m.get('outcome')
                if outcome and outcome.lower().startswith('p'):
                    test_classes[cls]['passing'].append(m.get('method') or '')
                else:
                    test_classes[cls]['failing'].append(m.get('method') or '')
                    if m.get('message'):
                        test_classes[cls]['errors'].append(str(m.get('message')))
                if m.get('time'):
                    try:
                        test_classes[cls]['time'] += float(m.get('time') or 0.0)
                    except Exception:
                        pass

    # build CSV rows
    rows = []
    all_seen_test_classes = list(test_classes.keys())

    for class_name, cov in coverage_map.items():
        total = cov.get('total')
        covered = cov.get('covered')
        not_covered = cov.get('not_covered')
        if total is None and covered is not None and not_covered is not None:
            total = covered + not_covered
        if total is None and covered is not None:
            total = covered

        percent = None
        try:
            if total and covered is not None:
                percent = round(float(covered) / float(total) * 100.0, 2)
        except Exception:
            percent = None

        # best-effort: list all test classes and aggregate passing/failing counts across them
        passing_methods = []
        failing_methods = []
        error_messages = []
        total_time = 0.0
        for tc, info in test_classes.items():
            passing_methods.extend([f"{tc}.{m}" for m in info['passing'] if m])
            failing_methods.extend([f"{tc}.{m}" for m in info['failing'] if m])
            error_messages.extend(info['errors'])
            total_time += info['time'] or 0.0

        rows.append({
            'class': class_name,
            'total_lines': total,
            'covered_lines': covered,
            'non_covered_lines': not_covered,
            'covered_percent': percent,
            'test_classes': ';'.join(all_seen_test_classes),
            'total_test_time_seconds': round(total_time, 3),
            'passing_methods': ';'.join(passing_methods),
            'failing_methods': ';'.join(failing_methods),
            'error_messages': ';'.join(error_messages),
        })

    # if there were no coverage entries, still output aggregated test-class level rows
    if not rows and test_classes:
        for tc, info in test_classes.items():
            rows.append({
                'class': tc,
                'total_lines': None,
                'covered_lines': None,
                'non_covered_lines': None,
                'covered_percent': None,
                'test_classes': tc,
                'total_test_time_seconds': round(info['time'] or 0.0, 3),
                'passing_methods': ';'.join(info['passing']),
                'failing_methods': ';'.join(info['failing']),
                'error_messages': ';'.join(info['errors']),
            })

    return rows


def aggregate_from_coverage_file(coverage_file):
    """Read one coverage JSON file and return simplified rows: class,total,covered,percent"""
    data = safe_load_json(coverage_file)
    entries = parse_coverage_json(data)
    rows = []
    for e in entries:
        name = e.get('name') or '(unknown)'
        total = e.get('total')
        covered = e.get('covered')
        raw = e.get('raw') or {}
        explicit_percent = None
        if isinstance(raw, dict) and '_explicit_covered_percent' in raw:
            explicit_percent = raw.get('_explicit_covered_percent')
        if total is None and covered is not None and e.get('not_covered') is not None:
            total = covered + e.get('not_covered')
        percent = None
        # prefer explicit percent when present
        if explicit_percent is not None:
            try:
                percent = round(float(explicit_percent), 2)
            except Exception:
                percent = None
        else:
            try:
                if total and covered is not None:
                    percent = round(float(covered) / float(total) * 100.0, 2)
            except Exception:
                percent = None
        rows.append({'class': name, 'total_lines': total, 'covered_lines': covered, 'covered_percent': percent})
    return rows


def write_csv(rows, out_path):
    fieldnames = ['class', 'total_lines', 'covered_lines', 'non_covered_lines', 'covered_percent',
                  'test_classes', 'total_test_time_seconds', 'passing_methods', 'failing_methods', 'error_messages']
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    def sanitize(val):
        if val is None:
            return ''
        if isinstance(val, (int, float)):
            return str(val)
        s = str(val)
        # remove any newlines that would break CSV viewers
        s = s.replace('\r', ' ').replace('\n', ' ')
        return s

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        # force quoting of all fields to avoid broken CSV when fields contain commas/newlines
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in rows:
            safe_row = {k: sanitize(r.get(k)) for k in fieldnames}
            writer.writerow(safe_row)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', default='test_results', help='Directory with test result and codecoverage files')
    p.add_argument('--output-file', default='test_results/coverage_summary.csv', help='CSV output file')
    p.add_argument('--coverage-file', default=None, help='Optional single coverage JSON file to read instead of scanning directory')
    args = p.parse_args()

    # If a coverage-file was provided, prefer it and produce a simplified CSV
    if args.coverage_file:
        if not os.path.isfile(args.coverage_file):
            print(f"Error: coverage file {args.coverage_file} does not exist", file=sys.stderr)
            sys.exit(2)
        rows = aggregate_from_coverage_file(args.coverage_file)
        # write simplified CSV with only the required columns
        simple_out = args.output_file
        # ensure header order for simplified CSV
        fieldnames = ['class', 'total_lines', 'covered_lines', 'covered_percent']
        os.makedirs(os.path.dirname(simple_out) or '.', exist_ok=True)
        with open(simple_out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for r in rows:
                # sanitize same as write_csv
                safe = {k: ('' if r.get(k) is None else str(r.get(k)).replace('\n', ' ').replace('\r', ' ')) for k in fieldnames}
                writer.writerow(safe)
        print(f"Wrote {len(rows)} rows to {simple_out}")
        return

    if not os.path.isdir(args.input_dir):
        print(f"Error: input dir {args.input_dir} does not exist or is not a directory", file=sys.stderr)
        sys.exit(2)

    rows = aggregate(args.input_dir)
    write_csv(rows, args.output_file)
    print(f"Wrote {len(rows)} rows to {args.output_file}")


if __name__ == '__main__':
    main()
