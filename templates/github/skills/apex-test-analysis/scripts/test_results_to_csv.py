#!/usr/bin/env python3
"""
Convert Salesforce Apex test results text file to CSV format.

Usage:
    python3 scripts/test_results_to_csv.py --input test_results/test-result.txt --output test_results/test_details.csv
"""
import argparse
import csv
import os
import re


def parse_test_results(input_file):
    """Parse test results text file and return list of result dictionaries."""

    results = []
    current_entry = None

    with open(input_file, 'r', encoding='utf-8') as f:
        # Iterate over raw lines so we can examine leading whitespace
        for raw in f:
            if raw is None:
                continue
            line_raw = raw.rstrip('\n')

            # Stop parsing once we hit the coverage section header
            if 'Apex Code Coverage by Class' in line_raw:
                # finalize current entry if present
                if current_entry:
                    if current_entry.get('stack_trace'):
                        if current_entry.get('message'):
                            current_entry['message'] += ' | Stack trace: ' + ' -> '.join(current_entry['stack_trace'])
                        else:
                            current_entry['message'] = 'Stack trace: ' + ' -> '.join(current_entry['stack_trace'])
                    results.append(current_entry)
                break

            if not line_raw.strip() or '===' in line_raw or '───' in line_raw or line_raw.strip().startswith('TEST NAME'):
                continue

            # Determine whether this is a new test entry.
            # A new entry usually starts at column 0 and does NOT start with the word 'Class'.
            is_new_entry = (not line_raw[:1].isspace()) and (not line_raw.strip().startswith('Class'))

            if is_new_entry:
                # finalize previous entry
                if current_entry:
                    # flush any collected stack trace into the message
                    if current_entry.get('stack_trace'):
                        if current_entry.get('message'):
                            current_entry['message'] += ' | Stack trace: ' + ' -> '.join(current_entry['stack_trace'])
                        else:
                            current_entry['message'] = 'Stack trace: ' + ' -> '.join(current_entry['stack_trace'])
                    results.append(current_entry)

                # Split on 2 or more spaces while preserving empty columns
                parts = [p.strip() for p in re.split(r'\s{2,}', line_raw.strip())]

                # Parse test name into class and method. If there is no '.', treat the value as the test class and leave method empty.
                test_name = parts[0] if parts else ''
                if '.' in test_name:
                    test_class, test_method = test_name.split('.', 1)
                else:
                    test_class, test_method = test_name, ''

                # Safely extract remaining columns, defaulting to empty strings so CSV columns don't shift
                # Special-case: sometimes parts[1] is directly the outcome (Pass/Fail) and no class_tested exists.
                test_class_tested = ''
                outcome = ''
                percent = ''
                message = ''
                runtime = ''

                if len(parts) > 1 and parts[1] in ('Pass', 'Fail'):
                    # parts layout: [test_name, outcome, percent?, message?, runtime?]
                    outcome = parts[1]
                    percent = parts[2] if len(parts) > 2 else ''
                    message = parts[3] if len(parts) > 3 else ''
                    runtime = parts[4] if len(parts) > 4 else ''
                else:
                    test_class_tested = parts[1] if len(parts) > 1 else ''
                    outcome = parts[2] if len(parts) > 2 else ''
                    percent = parts[3] if len(parts) > 3 else ''
                    message = parts[4] if len(parts) > 4 else ''
                    runtime = parts[5] if len(parts) > 5 else ''

                current_entry = {
                    'test_class': test_class,
                    'test_method': test_method,
                    'class_tested': test_class_tested,
                    'outcome': outcome,
                    'percent': percent.rstrip('%'),  # Remove % sign
                    'message': message,
                    'stack_trace': [],
                    'runtime': runtime
                }
            else:
                # Continuation lines: stack traces, messages, or runtime numbers
                stripped = line_raw.strip()
                if not current_entry:
                    # Ignore orphan continuation lines
                    continue

                # If the line begins with 'Class' it's a stack trace entry
                if stripped.startswith('Class'):
                    current_entry['stack_trace'].append(stripped)
                    continue

                # If it's a standalone number and runtime isn't set, treat as runtime
                if stripped.isdigit() and not current_entry.get('runtime'):
                    current_entry['runtime'] = stripped
                    continue

                # Otherwise append to the message
                msg = current_entry.get('message', '').strip()
                if msg:
                    msg += ' | ' + stripped
                else:
                    msg = stripped
                current_entry['message'] = msg

    # Don't forget the last entry
    if current_entry:
        results.append(current_entry)

    return results


def write_csv(results, output_file):
    """Write test results to CSV file."""
    fieldnames = ['test_class', 'test_method', 'class_tested', 'outcome', 'percent', 'message', 'runtime']
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in results:
            # Clean up percent field
            try:
                percent = float(r['percent'])
                r['percent'] = f"{percent:.1f}"  # Format to one decimal place
            except (ValueError, TypeError):
                r['percent'] = ''

            # Clean up message field
            msg = r.get('message', '').strip()
            stack_trace = [trace.strip() for trace in r.pop('stack_trace', [])]  # Clean stack trace
            stack_trace = [t for t in stack_trace if t]  # Remove empty entries
            
            # Clean up message by splitting on whitespace and joining with single spaces
            msg = ' '.join(msg.split())
            
            if stack_trace:
                # Remove runtime numbers from stack trace lines
                stack_trace = [t for t in stack_trace if not t.strip().isdigit()]
                
                if msg:
                    msg += ' | Stack trace: ' + ' -> '.join(stack_trace)
                else:
                    msg = 'Stack trace: ' + ' -> '.join(stack_trace)
            
            if msg:
                # Clean up message formatting and remove any extra whitespace
                msg_parts = [' '.join(p.split()) for p in msg.split('|')]  # Normalize whitespace
                msg_parts = [p.strip() for p in msg_parts if p and not p.isspace()]
                msg_parts = [p for p in msg_parts if not p.isdigit()]  # Remove standalone numbers
                r['message'] = ' | '.join(msg_parts)
            else:
                r['message'] = ''

            # Clean up runtime field
            runtime = r.get('runtime', '').strip()
            if runtime and runtime.isdigit():
                r['runtime'] = runtime
            else:
                r['runtime'] = ''

            writer.writerow(r)


def main():
    parser = argparse.ArgumentParser(description='Convert Salesforce test results to CSV')
    parser.add_argument('--input', required=True, help='Input test results text file')
    parser.add_argument('--output', required=True, help='Output CSV file')
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: input file {args.input} does not exist")
        return 1

    results = parse_test_results(args.input)
    write_csv(results, args.output)
    print(f"Wrote {len(results)} test results to {args.output}")
    return 0


if __name__ == '__main__':
    exit(main())