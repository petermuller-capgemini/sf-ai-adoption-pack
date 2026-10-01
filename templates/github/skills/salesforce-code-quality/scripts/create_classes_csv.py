#!/usr/bin/env python3
"""
Script to create code-quality/classes.csv with ClassName and TestClassName columns
based on the classes in the force-app folder
"""

import os
import csv
import re
from pathlib import Path

def extract_class_name_from_file(file_path):
    """Extract the class name from a .cls file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Look for class declaration patterns
        # Patterns: public class ClassName, global class ClassName, private class ClassName, etc.
        patterns = [
            r'(?:public|private|global|abstract|virtual)\s+(?:abstract\s+|virtual\s+)?class\s+(\w+)',
            r'class\s+(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def is_test_class(class_name, file_content=None):
    """Determine if a class is a test class based on naming conventions and content"""
    if not class_name:
        return False
        
    # Check naming patterns
    test_patterns = [
        r'.*Test$',
        r'.*_Test$', 
        r'.*test$',
        r'.*_test$',
        r'Test.*',
        r'.*Mock.*',
    ]
    
    for pattern in test_patterns:
        if re.match(pattern, class_name, re.IGNORECASE):
            return True
    
    # If we have file content, check for @isTest annotation
    if file_content:
        if re.search(r'@isTest', file_content, re.IGNORECASE):
            return True
            
    return False

def find_test_class_for_class(class_name, all_classes):
    """Find the corresponding test class for a given class"""
    if not class_name:
        return None
        
    # Common test class naming patterns
    possible_test_names = [
        f"{class_name}Test",
        f"{class_name}_Test", 
        f"{class_name}test",
        f"{class_name}_test",
        f"Test{class_name}",
        f"test{class_name}",
    ]
    
    # Check if any of the possible test names exist
    for test_name in possible_test_names:
        if test_name in all_classes:
            return test_name
            
    # Check for partial matches (e.g., Acme_SomeClass -> Acme_SomeClassTest)
    for existing_class in all_classes:
        if is_test_class(existing_class):
            # Remove common test suffixes to see if it matches our class
            base_name = re.sub(r'(Test|_Test|test|_test)$', '', existing_class, flags=re.IGNORECASE)
            if base_name == class_name:
                return existing_class
                
    return None

def main():
    # Set paths
    current_dir = Path(__file__).parent
    workspace_root = current_dir.parent
    classes_dir = workspace_root / "force-app" / "main" / "default" / "classes"
    output_dir = workspace_root / "code-quality"
    output_file = output_dir / "classes.csv"
    
    if not classes_dir.exists():
        print(f"Error: Classes directory not found at {classes_dir}")
        return
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print(f"Scanning classes in: {classes_dir}")
    
    # Get all .cls files
    cls_files = list(classes_dir.glob("*.cls"))
    print(f"Found {len(cls_files)} .cls files")
    
    # Extract class names and categorize
    all_classes = {}  # {class_name: file_path}
    test_classes = set()
    regular_classes = set()
    
    for cls_file in cls_files:
        class_name = extract_class_name_from_file(cls_file)
        if class_name:
            all_classes[class_name] = cls_file
            
            # Read file content to check for @isTest
            try:
                with open(cls_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if is_test_class(class_name, content):
                        test_classes.add(class_name)
                    else:
                        regular_classes.add(class_name)
            except Exception:
                # Fallback to name-based detection
                if is_test_class(class_name):
                    test_classes.add(class_name)
                else:
                    regular_classes.add(class_name)
    
    print(f"Found {len(regular_classes)} regular classes")
    print(f"Found {len(test_classes)} test classes")
    
    # Create CSV data
    csv_data = []
    
    # Process regular classes to find their test classes
    for class_name in sorted(regular_classes):
        test_class_name = find_test_class_for_class(class_name, all_classes.keys())
        
        csv_data.append({
            'ClassName': class_name,
            'TestClassName': test_class_name or ''
        })
    
    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ClassName', 'TestClassName']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"\nCreated {output_file} with {len(csv_data)} rows")
    
    # Print summary statistics
    classes_with_tests = sum(1 for row in csv_data if row['TestClassName'])
    classes_without_tests = len(csv_data) - classes_with_tests
    
    print(f"Classes with test classes: {classes_with_tests}")
    print(f"Classes without test classes: {classes_without_tests}")
    print(f"Test coverage: {classes_with_tests/len(csv_data)*100:.1f}%")
    
    # Show first few rows as preview
    print(f"\nFirst 10 rows preview:")
    print("ClassName,TestClassName")
    for i, row in enumerate(csv_data[:10]):
        print(f"{row['ClassName']},{row['TestClassName']}")
    
    # Show classes without tests
    if classes_without_tests > 0:
        print(f"\nClasses without test classes (first 10):")
        no_test_classes = [row['ClassName'] for row in csv_data if not row['TestClassName']]
        for class_name in no_test_classes[:10]:
            print(f"  - {class_name}")
        if len(no_test_classes) > 10:
            print(f"  ... and {len(no_test_classes) - 10} more")

if __name__ == "__main__":
    main()
