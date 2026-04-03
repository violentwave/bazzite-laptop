#!/usr/bin/env python3
"""Analyze test coverage gaps in the codebase."""

import os


def main():
    # Get all Python source files
    source_files = set()
    for root, dirs, files in os.walk('ai'):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.py') and file not in ('__init__.py', '__main__.py'):
                rel_path = os.path.relpath(os.path.join(root, file), 'ai')
                source_files.add(rel_path)

    # Get all test files
    test_files = set()
    for file in os.listdir('tests'):
        if file.startswith('test_') and file.endswith('.py'):
            test_files.add(file)

    # Find untested modules
    print('=== SOURCE FILES WITHOUT DIRECT TEST COVERAGE ===\n')
    untested = []

    for src in sorted(source_files):
        module_name = src.replace('/', '_').replace('.py', '')
        base_name = src.split('/')[-1].replace('.py', '')

        # Check various test naming patterns
        possible_tests = [
            f'test_{module_name}.py',
            f'test_{base_name}.py',
        ]

        has_test = any(t in test_files for t in possible_tests)

        if not has_test:
            untested.append(src)
            print(f'  - ai/{src}')

    print(f'\nTotal: {len(untested)}/{len(source_files)} source files lack direct tests')

    # Also show what's tested
    print('\n=== MODULES WITH TEST COVERAGE ===\n')
    tested = sorted(set(source_files) - set(untested))
    for src in tested[:20]:  # Show first 20
        print(f'  ✓ ai/{src}')
    if len(tested) > 20:
        print(f'  ... and {len(tested) - 20} more')

if __name__ == '__main__':
    main()
