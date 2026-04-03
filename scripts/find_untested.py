#!/usr/bin/env python3
"""Find untested modules."""
import os

# Get all source modules
source_files = []
for root, _dirs, files in os.walk('ai'):
    for f in files:
        if f.endswith('.py') and not f.startswith('__'):
            rel_path = os.path.join(root, f)
            module = rel_path.replace('ai/', '').replace('/', '_').replace('.py', '')
            source_files.append((module, rel_path))

# Get all test modules
test_files = set()
for f in os.listdir('tests'):
    if f.startswith('test_') and f.endswith('.py'):
        test_files.add(f.replace('test_', '').replace('.py', ''))

# Find untested
print("UNTESTED MODULES:")
print("-" * 60)
for module, path in sorted(source_files):
    if module not in test_files:
        print(f"{module:40s} {path}")
