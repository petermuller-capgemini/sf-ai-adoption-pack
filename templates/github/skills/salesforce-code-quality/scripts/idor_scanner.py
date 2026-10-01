#!/usr/bin/env python3
"""
IDOR (Insecure Direct Object Reference) Scanner for Salesforce Force-app
Scans all files in force-app directory for potential IDOR vulnerabilities

Usage:
    python3 idor_scanner.py                                    # Scan all files, output to CSV
    python3 idor_scanner.py --output terminal                  # Scan all files, output to terminal only
    python3 idor_scanner.py --files file1.cls file2.cls        # Scan specific files
    python3 idor_scanner.py --files file1.cls --output both    # Scan specific files, output to both CSV and terminal
"""

import os
import csv
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

class IDORScanner:
    def __init__(self, force_app_path):
        self.force_app_path = Path(force_app_path)
        self.violations = []

        # IDOR vulnerability patterns for Salesforce
        self.patterns = {
            # Critical Issues
            'class_no_sharing_model': {
                'pattern': r'(?:^|\n)\s*public\s+class\s+\w+(?!\s+(?:with|without|inherited)\s+sharing)',
                'severity': 'Critical',
                'description': 'Class doesn\'t specify sharing model'
            },
            'class_without_sharing_no_justification': {
                'pattern': r'(?:^|\n)(?!.*JUSTIFICATION.*\n)(?:.*\*\/\n)?\s*public\s+without\s+sharing\s+class\s+(\w+)',
                'severity': 'Critical',
                'description': 'Class uses without sharing without justification'
            },
            'soql_injection_risk': {
                'pattern': r'Database\.query\s*\([^)]*\+[^)]*\)|SELECT\s+[^;]+\s+WHERE\s+[^;]*\+[^;]*[\'"]',
                'severity': 'Critical',
                'description': 'Dynamic SOQL without proper sanitization'
            },
            'missing_security_enforced': {
                'pattern': r'\[\s*SELECT\s+[^\]]{1,500}?\s+FROM\s+\w+[^\]]{0,500}?WHERE[^\]]{0,500}?\s*[\];]',
                'severity': 'Critical',
                'description': 'Inconsistent or missing SOQL and DML security enforcement'
            },
            'idor_with_sharing_no_requery': {
                'pattern': r'@AuraEnabled[^\n]{0,100}\n[^\n]{0,200}(?:public|private|global)\s+(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]{0,200}(?:Id|String)\s+\w*[Ii]d\w*[^)]{0,100}\)',
                'severity': 'Critical',
                'description': 'Insecure Direct Object Reference - Class declared with sharing but record ID not re-queried'
            },
            'idor_without_sharing_with_requery': {
                'pattern': r'without\s+sharing\s+class[^{]{0,100}\{[^}]{0,2000}SELECT[^}]{0,500}WHERE\s+Id\s*=\s*:[^}]{0,200}WITH\s+SECURITY_ENFORCED',
                'severity': 'Critical',
                'description': 'Insecure Direct Object Reference - Record being re-queried despite declaring without sharing'
            },
            'idor_no_requery_operations': {
                'pattern': r'@AuraEnabled[^\n]{0,100}\n[^\n]{0,200}(?:public|private|global)\s+(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]{0,200}(?:Id|String)\s+\w*[Ii]d\w*[^)]{0,100}\)',
                'severity': 'Critical',
                'description': 'Insecure Direct Object Reference - Not re-querying record and proceed to perform operations'
            },
            'method_accepts_userid': {
                'pattern': r'@AuraEnabled[^\n]{0,100}\n[^\n]{0,200}(?:public|private|global)\s+(?:static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]{0,200}(?:Id|String)\s+userId[^)]{0,100}\)',
                'severity': 'Critical',
                'description': 'Methods accept userId parameter directly'
            },

            # High Issues
            'dml_in_loop': {
                'pattern': r'for\s*\([^)]+\)\s*\{[^}]{0,500}\b(?:insert|update|delete|upsert)\s+(?!new\s)\w+\s*;',
                'severity': 'High',
                'description': 'DML operation inside loop'
            },
            'email_in_loop': {
                'pattern': r'for\s*\([^)]+\)\s*\{[\s\S]{0,3000}?(?:Messaging\.sendEmail|Acme_EmailMessageService\.sendEmailMessages)[\s\S]{0,500}?\n\s*\}',
                'severity': 'High',
                'description': 'Email service call inside loop'
            },
            'queueable_in_loop': {
                'pattern': r'for\s*\([^)]+\)\s*\{[^}]{0,500}System\.enqueueJob',
                'severity': 'High',
                'description': 'Misplaced queueable job call'
            },
            'missing_input_validation': {
                'pattern': r'Integer\.valueOf\s*\(\s*\w+\s*\*\s*\d+\s*\)',
                'severity': 'High',
                'description': 'Missing input validation'
            },
            'potential_null_pointer': {
                'pattern': r'(?:Map|List)<[^>]+>\.get\([^)]+\)\.(?!isEmpty|size)\w+',
                'severity': 'High',
                'description': 'Potential null pointer exception'
            },
            'soql_in_loop': {
                'pattern': r'for\s*\([^)]+\)\s*\{[^}]{0,500}\[SELECT',
                'severity': 'High',
                'description': 'SOQL in loop'
            },
            'hardcoded_references': {
                'pattern': r'(?:templateMap\.get\s*\(\s*[\'"][a-zA-Z0-9_]{20,}[\'"]|[\'"][0-9A-Za-z]{15,18}[\'"])',
                'severity': 'High',
                'description': 'Hardcoded references'
            },
            'http_callout_no_validation': {
                'pattern': r'HttpRequest\s+\w+\s*=\s*new\s+HttpRequest\(\)[^;]{0,500}http\.send\(\w+\)',
                'severity': 'Critical',
                'description': 'Missing checks for HTTP callouts'
            },

            # Medium Issues
            'missing_recursion_guard': {
                'pattern': r'(?:^|\n)\s*public\s+class\s+(\w+TriggerHandler)(?!\s+extends\s+Acme_TriggerHandler)',
                'severity': 'Medium',
                'description': 'Missing recursion guard and not extending Acme_TriggerHandler'
            },
            'inconsistent_error_handling': {
                'pattern': r'catch\s*\([^)]+\)\s*\{(?![^}]{0,200}LOGGER)[^}]{0,200}\}',
                'severity': 'Medium',
                'description': 'Inconsistent or missing error handling'
            },
            'outdated_api_version': {
                'pattern': r'apiVersion>\s*(?:[1-4][0-9]|5[0-7])\.0\s*<',
                'severity': 'Medium',
                'description': 'Component is using an outdated API version'
            },

            # Low Issues
            'inconsistent_logger_usage': {
                'pattern': r'System\.debug\(',
                'severity': 'Low',
                'description': 'Inconsistent logger usage'
            },
            'commented_code': {
                'pattern': r'^\s*//\s*(?!.*?(?:@param|@return|@description|TODO|FIXME|NOTE|Added|Updated|Fixed)).*?(?:if\s*\(|for\s*\(|while\s*\(|SELECT\s+|INSERT\s+|UPDATE\s+|DELETE\s+)',
                'severity': 'Low',
                'description': 'Commented out or unused code'
            }
        }

    def scan_file(self, file_path):
        """Scan a single file for IDOR vulnerabilities"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            file_violations = []
            lines = content.split('\n')

            for pattern_name, pattern_info in self.patterns.items():
                matches = re.finditer(pattern_info['pattern'], content, re.IGNORECASE | re.MULTILINE | re.DOTALL)

                for match in matches:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                    # Skip false positives
                    if self._is_false_positive(pattern_name, match, content, line_num):
                        continue

                    violation = {
                        'file_path': str(file_path.relative_to(self.force_app_path)),
                        'line_number': line_num,
                        'violation_type': pattern_name,
                        'severity': pattern_info['severity'],
                        'description': pattern_info['description'],
                        'code_snippet': line_content,
                        'match_text': match.group(0),
                        'scan_time': datetime.now().isoformat()
                    }
                    file_violations.append(violation)

            return file_violations

        except Exception as e:
            print(f"Error scanning {file_path}: {str(e)}")
            return []

    def _is_false_positive(self, pattern_name, match, content, line_num):
        """Check if a match is a false positive"""
        match_text = match.group(0)

        # Check for WITH SECURITY_ENFORCED that might be on a different line
        if pattern_name == 'missing_security_enforced':
            # Extract the full query including potential line breaks
            query_start = match.start()
            query_end = match.end()
            # Look ahead up to 200 chars for WITH SECURITY_ENFORCED
            extended_text = content[query_start:min(query_end + 200, len(content))]
            if re.search(r'WITH\s+(?:SECURITY_ENFORCED|USER_MODE)', extended_text, re.IGNORECASE):
                return True

        # Check for shared utility-controller DML operations (not real DML in loops)
        if pattern_name == 'dml_in_loop':
            # Look for Acme_UtilityController method calls in the loop context
            loop_start = match.start()
            loop_context = content[loop_start:min(loop_start + 1000, len(content))]
            if 'Acme_UtilityController' in loop_context:
                return True

        # Check for justification comment before without sharing
        if pattern_name == 'class_without_sharing_no_justification':
            # Look back 500 chars for JUSTIFICATION comment
            before_text = content[max(0, match.start() - 500):match.start()]
            if re.search(r'JUSTIFICATION|without\s+sharing\s+because', before_text, re.IGNORECASE):
                return True

        # Ignore descriptive comments (not actual code)
        if pattern_name == 'commented_code':
            # Check if it's a descriptive comment
            if any(keyword in match_text.lower() for keyword in [
                'query', 'match', 'split', 'map', 'hold', 'populate', 
                'list', 'process', 'store', 'update', 'create', 'insert',
                'append', 'remove', 'no match', 'found'
            ]):
                return True

        return False

    def scan_directory(self, specific_files=None):
        """Scan all relevant files in the force-app directory or specific files"""
        # File extensions to scan
        extensions = ['.cls', '.trigger', '.cmp', '.js', '.page', '.vfp', '.apex']

        if specific_files:
            # Scan only specific files
            print(f"Scanning {len(specific_files)} specific file(s)...")
            for file_spec in specific_files:
                file_path = Path(file_spec)

                # If path is relative, check in force-app
                if not file_path.is_absolute():
                    file_path = self.force_app_path / file_path

                if not file_path.exists():
                    print(f"Warning: File not found: {file_spec}")
                    continue

                if not any(str(file_path).lower().endswith(ext) for ext in extensions):
                    print(f"Warning: Skipping unsupported file type: {file_spec}")
                    continue

                print(f"Scanning: {file_path}")
                violations = self.scan_file(file_path)
                self.violations.extend(violations)
        else:
            # Scan entire directory
            print(f"Scanning directory: {self.force_app_path}")

            for root, dirs, files in os.walk(self.force_app_path):
                for file in files:
                    file_path = Path(root) / file

                    # Check if file has relevant extension
                    if any(file.lower().endswith(ext) for ext in extensions):
                        print(f"Scanning: {file_path.relative_to(self.force_app_path)}")
                        violations = self.scan_file(file_path)
                        self.violations.extend(violations)

    def save_to_csv(self, output_file):
        """Save violations to CSV file"""
        if not self.violations:
            print("No violations found!")
            # Create empty CSV with headers
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = ['file_path', 'line_number', 'violation_type', 'severity', 
                            'description', 'code_snippet', 'match_text', 'scan_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            return

        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['file_path', 'line_number', 'violation_type', 'severity', 
                         'description', 'code_snippet', 'match_text', 'scan_time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for violation in self.violations:
                writer.writerow(violation)

        print(f"Saved {len(self.violations)} violations to {output_file}")

    def print_summary(self):
        """Print summary of violations found"""
        if not self.violations:
            print("\n✓ No IDOR violations found!")
            return

        severity_counts = {}
        type_counts = {}

        for violation in self.violations:
            severity = violation['severity']
            vtype = violation['violation_type']

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[vtype] = type_counts.get(vtype, 0) + 1

        print("\n" + "="*60)
        print("IDOR SCAN SUMMARY")
        print("="*60)
        print(f"Total violations found: {len(self.violations)}")

        print("\nBy Severity:")
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity in severity_counts:
                print(f"  {severity:10s}: {severity_counts[severity]:4d}")

        print("\nBy Type:")
        for vtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype:50s}: {count:4d}")
        print("="*60)

    def print_detailed_violations(self):
        """Print detailed list of all violations to terminal"""
        if not self.violations:
            print("\n✓ No violations to display")
            return

        # Group by severity
        by_severity = {}
        for v in self.violations:
            severity = v['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(v)

        print("\n" + "="*80)
        print("DETAILED VIOLATIONS REPORT")
        print("="*80)

        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity not in by_severity:
                continue

            violations_list = by_severity[severity]
            print(f"\n{severity.upper()} SEVERITY ({len(violations_list)} issues)")
            print("-"*80)

            for v in violations_list:
                print(f"\n  File: {v['file_path']}")
                print(f"  Line: {v['line_number']}")
                print(f"  Type: {v['violation_type']}")
                print(f"  Desc: {v['description']}")
                print(f"  Code: {v['code_snippet'][:100]}...")
                print()

        print("="*80)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='IDOR Scanner for Salesforce Force-app',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all files, save to CSV
  python3 idor_scanner.py

  # Scan all files, output to terminal only
  python3 idor_scanner.py --output terminal

  # Scan specific files
  python3 idor_scanner.py --files Acme_AccountService.cls Acme_ContactService.cls

  # Scan specific files with full path
  python3 idor_scanner.py --files force-app/main/default/classes/Acme_B2BUtils.cls

  # Output to both CSV and terminal
  python3 idor_scanner.py --output both

  # Scan specific files, terminal only
  python3 idor_scanner.py --files Acme_*.cls --output terminal
        """
    )

    parser.add_argument(
        '--files',
        nargs='+',
        help='Specific files to scan (relative to force-app or absolute paths)'
    )

    parser.add_argument(
        '--output',
        choices=['csv', 'terminal', 'both'],
        default='csv',
        help='Output method: csv (default), terminal, or both'
    )

    parser.add_argument(
        '--output-file',
        type=str,
        help='Custom output CSV file path (default: idor_violations.csv in workspace root)'
    )

    args = parser.parse_args()

    # Set paths
    current_dir = Path(__file__).parent
    workspace_root = current_dir.parent
    force_app_path = workspace_root / "force-app"

    # Determine output file path
    if args.output_file:
        output_file = Path(args.output_file)
    else:
        output_file = workspace_root / "idor_violations.csv"

    if not force_app_path.exists():
        print(f"Error: force-app directory not found at {force_app_path}")
        return

    # Print scan configuration
    print("="*60)
    print("IDOR Vulnerability Scanner")
    print("="*60)
    if args.files:
        print(f"Mode: Scanning {len(args.files)} specific file(s)")
        for f in args.files:
            print(f"  - {f}")
    else:
        print(f"Mode: Scanning entire codebase")
    print(f"Output: {args.output}")
    if args.output in ['csv', 'both']:
        print(f"CSV File: {output_file}")
    print("="*60 + "\n")

    # Initialize and run scanner
    scanner = IDORScanner(force_app_path)
    scanner.scan_directory(specific_files=args.files)

    # Output results based on selected method
    if args.output in ['csv', 'both']:
        scanner.save_to_csv(output_file)

    if args.output in ['terminal', 'both']:
        scanner.print_detailed_violations()

    # Always print summary
    scanner.print_summary()

    # Final message
    if args.output == 'csv':
        print(f"\n✓ Scan complete! Results saved to: {output_file}")
    elif args.output == 'terminal':
        print(f"\n✓ Scan complete! Results displayed above.")
    else:
        print(f"\n✓ Scan complete! Results saved to {output_file} and displayed above.")

if __name__ == "__main__":
    main()
