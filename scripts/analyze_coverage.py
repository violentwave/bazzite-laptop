#!/usr/bin/env python3
"""Analyze test coverage gaps by comparing source and test files."""

import ast
import json
import re
from pathlib import Path


def extract_functions_classes(filepath: Path) -> dict:
    """Extract all functions and classes from a Python file."""
    try:
        with open(filepath) as f:
            tree = ast.parse(f.read())
    except Exception as e:
        return {"error": str(e), "functions": [], "classes": []}

    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Skip private/dunder methods unless they're special
            is_dunder = node.name.startswith("__") and node.name.endswith("__")
            if not node.name.startswith("_") or is_dunder:
                functions.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            is_dunder = node.name.startswith("__") and node.name.endswith("__")
            if not node.name.startswith("_") or is_dunder:
                functions.append(f"async {node.name}")
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                classes.append(node.name)

    return {"functions": functions, "classes": classes}


def extract_test_coverage(filepath: Path) -> dict:
    """Extract what's tested from a test file."""
    try:
        with open(filepath) as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e), "tested_functions": [], "tested_classes": []}

    # Find test functions and classes
    test_funcs = re.findall(r"def (test_\w+)", content)
    test_classes = re.findall(r"class (Test\w+)", content)

    # Extract what's being imported from the source
    imports = re.findall(r"from ai\.[\w.]+ import (.+)", content)
    imported_items = []
    for imp in imports:
        # Handle multi-line imports
        items = [i.strip() for i in imp.split(",")]
        imported_items.extend(items)

    return {
        "test_functions": test_funcs,
        "test_classes": test_classes,
        "imports": imported_items,
    }


def main():
    project_root = Path("/var/home/lch/projects/bazzite-laptop")
    ai_dir = project_root / "ai"
    tests_dir = project_root / "tests"

    # Map source files to test files
    source_files = sorted(ai_dir.rglob("*.py"))
    source_files = [f for f in source_files if "__" not in f.name and not f.name.startswith("_")]

    print("# Test Coverage Gap Analysis\n")
    print(f"Found {len(source_files)} source files in ai/\n")

    gaps = []

    for src_file in source_files:
        rel_path = src_file.relative_to(ai_dir)
        module_path = str(rel_path.with_suffix("")).replace("/", ".")

        # Try to find corresponding test file
        test_file_name = f"test_{rel_path.stem}.py"
        test_file = tests_dir / test_file_name

        src_info = extract_functions_classes(src_file)

        if not src_info["functions"] and not src_info["classes"]:
            continue

        if not test_file.exists():
            gaps.append({
                "module": f"ai.{module_path}",
                "file": str(rel_path),
                "test_file": test_file_name,
                "status": "NO_TEST_FILE",
                "functions": src_info["functions"],
                "classes": src_info["classes"],
            })
        else:
            test_info = extract_test_coverage(test_file)
            gaps.append({
                "module": f"ai.{module_path}",
                "file": str(rel_path),
                "test_file": test_file_name,
                "status": "HAS_TESTS",
                "functions": src_info["functions"],
                "classes": src_info["classes"],
                "test_coverage": test_info,
            })

    # Print gaps
    print("## Files Without Test Files")
    no_tests = [g for g in gaps if g["status"] == "NO_TEST_FILE"]
    for gap in no_tests:
        print(f"\n### {gap['module']}")
        print(f"File: `{gap['file']}`")
        print(f"Missing test file: `{gap['test_file']}`")
        if gap["functions"]:
            print(f"Functions ({len(gap['functions'])}): {', '.join(gap['functions'][:5])}")
        if gap["classes"]:
            print(f"Classes ({len(gap['classes'])}): {', '.join(gap['classes'][:5])}")

    print("\n\n## Summary")
    print(f"- Total source modules analyzed: {len(gaps)}")
    print(f"- Modules without test files: {len(no_tests)}")
    print(f"- Modules with test files: {len([g for g in gaps if g['status'] == 'HAS_TESTS'])}")

    # Export detailed JSON
    output_file = project_root / "docs" / "test-coverage-analysis.md"

    with open(output_file, "w") as f:
        f.write("# Test Coverage Gap Analysis\n\n")
        f.write(f"Generated: {Path(__file__).name}\n\n")

        f.write("## Modules Without Test Files\n\n")
        for gap in no_tests:
            f.write(f"### {gap['module']}\n\n")
            f.write(f"- **File**: `{gap['file']}`\n")
            f.write(f"- **Missing test**: `tests/{gap['test_file']}`\n")
            if gap["functions"]:
                fns = ', '.join(gap['functions'])
                f.write(f"- **Functions** ({len(gap['functions'])}): {fns}\n")
            if gap["classes"]:
                f.write(f"- **Classes** ({len(gap['classes'])}): {', '.join(gap['classes'])}\n")
            f.write("\n")

        f.write("\n## Detailed Coverage Data\n\n")
        f.write("```json\n")
        f.write(json.dumps(gaps, indent=2))
        f.write("\n```\n")

    print(f"\nDetailed report written to: {output_file}")


if __name__ == "__main__":
    main()
