import json
import csv
import os
import sys

IN = 'qa-result/test-result-codecoverage.json'
OUT = 'qa-result/test-result-codecoverage.csv'

if not os.path.isfile(IN):
    sys.exit(f'Input file not found: {IN}')

with open(IN, 'r', encoding='utf-8') as f:
    data = json.load(f)

os.makedirs(os.path.dirname(OUT), exist_ok=True)

with open(OUT, 'w', newline='', encoding='utf-8') as csvf:
    writer = csv.writer(csvf)
    writer.writerow(['name', 'totalLines', 'totalCovered', 'coveredPercent'])
    for obj in data:
        writer.writerow([
            obj.get('name', ''),
            obj.get('totalLines', ''),
            obj.get('totalCovered', ''),
            obj.get('coveredPercent', '')
        ])

print(f'Wrote {OUT}')