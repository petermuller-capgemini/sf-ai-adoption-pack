#!/usr/bin/env python3
"""
Compare data between two Salesforce orgs.

This script queries objects from two orgs and generates
comparison reports showing differences in records, fields, and metadata.
"""

import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def run_soql_query(org_alias, query):
    """
    Execute a SOQL query against the specified org using Salesforce CLI.

    Args:
        org_alias: The org alias to query against
        query: The SOQL query string

    Returns:
        List of records from the query result
    """
    try:
        # Remove trailing whitespace from query
        query = query.strip()

        cmd = [
            'sf', 'data', 'query',
            '--query', query,
            '--target-org', org_alias,
            '--result-format', 'json'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        return data.get('result', {}).get('records', [])
    except subprocess.CalledProcessError as e:
        print(f"Error querying {org_alias}: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response from {org_alias}: {e}", file=sys.stderr)
        return []


def get_products(org_alias, include_inactive=False, custom_query=None, key_field=None):
    """
    Retrieve all Product2 records from the specified org.

    Args:
        org_alias: The org alias to query
        include_inactive: Whether to include inactive products
        custom_query: Optional custom SOQL query to use instead of default
        key_field: Field name to use as the key for indexing records (default: ProductCode, fallback to Id)

    Returns:
        Dictionary mapping key_field to product record
    """
    if custom_query:
        query = custom_query
    else:
        where_clause = "" if include_inactive else "WHERE IsActive = TRUE"

        query = f"""
            SELECT Id, Name, ProductCode, Description, Family, IsActive,
                   CreatedDate, LastModifiedDate, QuantityUnitOfMeasure,
                   StockKeepingUnit, ExternalId, ExternalDataSourceId
            FROM Product2
            {where_clause}
            ORDER BY ProductCode
        """

    records = run_soql_query(org_alias, query)
    print(f"  Retrieved {len(records)} records from query")

    # Determine which field to use as the key
    if key_field:
        print(f"  Using '{key_field}' as the key field")
    else:
        key_field = 'ProductCode'
        print(f"  Using default key field: '{key_field}' (fallback to 'Id')")

    # Index by specified key field (or Id if key field is null)
    products = {}
    duplicates = 0
    null_keys = 0
    
    for record in records:
        # Remove attributes metadata
        if 'attributes' in record:
            del record['attributes']

        # Get the key value, with fallback to Id if not specified or null
        key_value = record.get(key_field)
        if key_value is None:
            null_keys += 1
            key_value = record.get('Id')
            
        if key_value in products:
            duplicates += 1
            print(f"  WARNING: Duplicate key found: {key_value}")
        products[key_value] = record

    if null_keys > 0:
        print(f"  INFO: {null_keys} records had null {key_field}, used Id instead")
    if duplicates > 0:
        print(f"  WARNING: {duplicates} duplicate keys found - records were overwritten")
    print(f"  Indexed {len(products)} unique records")

    return products


def get_pricebook_entries(org_alias, product_ids):
    """
    Retrieve PricebookEntry records for the specified products.

    Args:
        org_alias: The org alias to query
        product_ids: List of Product2 Ids

    Returns:
        Dictionary mapping Product2Id to list of pricebook entries
    """
    if not product_ids:
        return {}

    # Split into chunks of 100 to avoid SOQL query length limits
    chunk_size = 100
    all_entries = []

    for i in range(0, len(product_ids), chunk_size):
        chunk = product_ids[i:i + chunk_size]
        ids_str = "','".join(chunk)

        query = f"""
            SELECT Id, Product2Id, Pricebook2Id, Pricebook2.Name,
                   UnitPrice, IsActive, UseStandardPrice
            FROM PricebookEntry
            WHERE Product2Id IN ('{ids_str}')
        """

        entries = run_soql_query(org_alias, query)
        all_entries.extend(entries)

    # Group by Product2Id
    entries_by_product = defaultdict(list)
    for entry in all_entries:
        if 'attributes' in entry:
            del entry['attributes']
        entries_by_product[entry['Product2Id']].append(entry)

    return entries_by_product


def compare_products(org1_products, org2_products, org1_name, org2_name, ignore_fields=None):
    """
    Compare products between two orgs and identify differences.

    Args:
        org1_products: Products from first org
        org2_products: Products from second org
        org1_name: Name of first org
        org2_name: Name of second org
        ignore_fields: Set of field names to ignore in comparison

    Returns:
        Dictionary with comparison results
    """
    if ignore_fields is None:
        ignore_fields = {'Id', 'CreatedDate', 'LastModifiedDate'}

    comparison = {
        'only_in_org1': [],
        'only_in_org2': [],
        'in_both': [],
        'different_fields': []
    }

    all_keys = set(org1_products.keys()) | set(org2_products.keys())

    for key in sorted(all_keys):
        if key in org1_products and key in org2_products:
            comparison['in_both'].append(key)

            # Compare field values
            prod1 = org1_products[key]
            prod2 = org2_products[key]

            differences = {}
            for field in prod1.keys():
                if field in ignore_fields:
                    continue

                val1 = prod1.get(field)
                val2 = prod2.get(field)

                if val1 != val2:
                    differences[field] = {
                        org1_name: val1,
                        org2_name: val2
                    }

            if differences:
                comparison['different_fields'].append({
                    'product_code': key,
                    'name': prod1.get('Name'),
                    'differences': differences
                })

        elif key in org1_products:
            comparison['only_in_org1'].append(key)
        else:
            comparison['only_in_org2'].append(key)

    return comparison


def write_summary_report(comparison, org1_name, org2_name, output_file):
    """Write a summary report of the comparison."""
    with open(output_file, 'w') as f:
        f.write("Record Comparison Report\n")
        f.write("========================\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Org 1: {org1_name}\n")
        f.write(f"Org 2: {org2_name}\n\n")

        f.write("Summary Statistics\n")
        f.write("------------------\n")
        f.write(f"Records only in {org1_name}: {len(comparison['only_in_org1'])}\n")
        f.write(f"Records only in {org2_name}: {len(comparison['only_in_org2'])}\n")
        f.write(f"Records in both orgs: {len(comparison['in_both'])}\n")
        f.write(f"Records with differences: {len(comparison['different_fields'])}\n\n")

        if comparison['only_in_org1']:
            f.write(f"\nRecords only in {org1_name}:\n")
            f.write("-" * 50 + "\n")
            for code in comparison['only_in_org1']:
                f.write(f"  - {code}\n")

        if comparison['only_in_org2']:
            f.write(f"\nRecords only in {org2_name}:\n")
            f.write("-" * 50 + "\n")
            for code in comparison['only_in_org2']:
                f.write(f"  - {code}\n")

        if comparison['different_fields']:
            f.write("\nRecords with field differences:\n")
            f.write("-" * 50 + "\n")
            for item in comparison['different_fields']:
                f.write(f"\nRecord: {item['product_code']} ({item['name']})\n")
                for field, values in item['differences'].items():
                    f.write(f"  {field}:\n")
                    f.write(f"    {org1_name}: {values[org1_name]}\n")
                    f.write(f"    {org2_name}: {values[org2_name]}\n")


def write_detailed_csv(comparison, org1_products, org2_products, org1_name, org2_name, output_file):
    """Write detailed comparison to CSV."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ProductCode', 'Name', 'Status', 'Field',
            f'{org1_name}_Value', f'{org2_name}_Value'
        ])

        # Products only in org1
        for code in comparison['only_in_org1']:
            prod = org1_products[code]
            writer.writerow([
                code, prod.get('Name'), f'Only in {org1_name}', '', '', ''
            ])

        # Products only in org2
        for code in comparison['only_in_org2']:
            prod = org2_products[code]
            writer.writerow([
                code, prod.get('Name'), f'Only in {org2_name}', '', '', ''
            ])

        # Products with differences
        for item in comparison['different_fields']:
            code = item['product_code']
            name = item['name']

            for field, values in item['differences'].items():
                writer.writerow([
                    code, name, 'Different', field,
                    values[org1_name], values[org2_name]
                ])


def main():
    parser = argparse.ArgumentParser(
        description='Compare data between two Salesforce orgs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare products between two orgs
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2

  # Include inactive records
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --include-inactive

  # Use custom SOQL query
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --query "SELECT Name, CurrencyIsoCode, IsActive, IsArchived, Description, IsStandard, ValidFrom, ValidTo, {{APEX_PREFIX}}_Deprecated_Legacy_Data__c, {{APEX_PREFIX}}_SourceID__c, {{APEX_PREFIX}}_Is_Migrated__c FROM Pricebook2"

  # Use Name as the key field for comparison
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --query "SELECT Name, IsActive FROM Pricebook2" --key-field Name

  # Ignore additional fields in comparison
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --ignore-fields Id CreatedDate LastModifiedDate Description

  # Specify custom output directory
  python3 scripts/compare_products.py --org1 sandbox1 --org2 sandbox2 --output-dir comparison_results
        """
    )

    parser.add_argument('--org1', required=True,
                        help='First org alias (e.g., sandbox1)')
    parser.add_argument('--org2', required=True,
                        help='Second org alias (e.g., sandbox2)')
    parser.add_argument('--include-inactive', action='store_true',
                        help='Include inactive records in comparison')
    parser.add_argument('--output-dir', default='product_comparison',
                        help='Output directory for comparison reports (default: product_comparison)')
    parser.add_argument('--include-pricing', action='store_true',
                        help='Also compare pricebook entries (slower)')
    parser.add_argument('--query', '--custom-query',
                        help='Custom SOQL query to use instead of default Product2 query')
    parser.add_argument('--ignore-fields', nargs='+',
                        default=['Id', 'CreatedDate', 'LastModifiedDate'],
                        help='Fields to ignore in comparison (default: Id CreatedDate LastModifiedDate)')
    parser.add_argument('--key-field',
                        help='Field to use as the key for comparing records (default: ProductCode with fallback to Id). Examples: Name, ProductCode, Id')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Comparing records between {args.org1} and {args.org2}...")
    print(f"Output directory: {output_dir}")
    if args.query:
        print(f"Using custom query")
    if args.key_field:
        print(f"Using key field: {args.key_field}")
    print(f"Ignoring fields: {', '.join(args.ignore_fields)}")

    # Fetch products from both orgs
    print(f"\nFetching records from {args.org1}...")
    org1_products = get_products(args.org1, args.include_inactive, args.query, args.key_field)
    print(f"  Final count: {len(org1_products)} unique records")

    print(f"\nFetching records from {args.org2}...")
    org2_products = get_products(args.org2, args.include_inactive, args.query, args.key_field)
    print(f"  Final count: {len(org2_products)} unique records")

    # Compare products
    print("\nComparing records...")
    ignore_fields = set(args.ignore_fields)
    comparison = compare_products(org1_products, org2_products, args.org1, args.org2, ignore_fields)

    # Write reports
    summary_file = output_dir / 'comparison_summary.txt'
    csv_file = output_dir / 'comparison_details.csv'

    print(f"\nWriting summary report to {summary_file}...")
    write_summary_report(comparison, args.org1, args.org2, summary_file)

    print(f"Writing detailed CSV to {csv_file}...")
    write_detailed_csv(comparison, org1_products, org2_products, args.org1, args.org2, csv_file)

    # Print summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"Records only in {args.org1}: {len(comparison['only_in_org1'])}")
    print(f"Records only in {args.org2}: {len(comparison['only_in_org2'])}")
    print(f"Records in both orgs: {len(comparison['in_both'])}")
    print(f"Records with differences: {len(comparison['different_fields'])}")
    print(f"\nReports saved to: {output_dir}")

    # Optionally compare pricing
    if args.include_pricing:
        print("\nFetching pricebook entries (this may take a while)...")
        org1_ids = [p['Id'] for p in org1_products.values()]
        org2_ids = [p['Id'] for p in org2_products.values()]

        org1_pricing = get_pricebook_entries(args.org1, org1_ids)
        org2_pricing = get_pricebook_entries(args.org2, org2_ids)

        pricing_file = output_dir / 'pricing_comparison.json'
        print(f"Writing pricing comparison to {pricing_file}...")

        with open(pricing_file, 'w') as f:
            json.dump({
                args.org1: {k: v for k, v in org1_pricing.items()},
                args.org2: {k: v for k, v in org2_pricing.items()}
            }, f, indent=2, default=str)


if __name__ == '__main__':
    main()
