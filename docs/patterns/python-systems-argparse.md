---
language: python
domain: systems
type: pattern
title: CLI argument parsing with argparse
tags: argparse, cli, argument-parser, command-line
---

# CLI Argument Parsing with argparse

Build robust command-line interfaces using Python's built-in argparse module.

## Basic Argument Parser

```python
import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="My application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--count", type=int, default=10, help="Count (default: 10)")
    
    return parser

args = create_parser().parse_args()
print(f"Input: {args.input}")
print(f"Verbose: {args.verbose}")
```

## Subcommands

```python
import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Subcommand: install
    install_parser = subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument("package", help="Package name")
    install_parser.add_argument("--force", action="store_true", help="Force install")
    
    # Subcommand: remove
    remove_parser = subparsers.add_parser("remove", help="Remove a package")
    remove_parser.add_argument("package", help="Package name")
    
    return parser

args = create_parser().parse_args()

if args.command == "install":
    install_package(args.package, force=args.force)
elif args.command == "remove":
    remove_package(args.package)
```

## Validation

```python
import argparse
from pathlib import Path

def validate_path(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"File not found: {path}")
    return p

def validate_port(port: str) -> int:
    try:
        p = int(port)
        if not 1 <= p <= 65535:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port: {port}")
    return p

parser = argparse.ArgumentParser()
parser.add_argument("config", type=validate_path, help="Config file")
parser.add_argument("-p", "--port", type=validate_port, default=8080)
```

## Type Conversion

```python
parser = argparse.ArgumentParser()

# Boolean flag
parser.add_argument("--debug", action="store_true", default=False)
parser.add_argument("--no-debug", dest="debug", action="store_false")

# List argument
parser.add_argument("--tags", nargs="+", default=[])

# Optional with value
parser.add_argument("--level", choices=["low", "medium", "high"], default="medium")
```

## Environment Variable Defaults

```python
import os

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-key",
        default=os.environ.get("API_KEY", "default-key"),
        help="API key (default: from API_KEY env)",
    )
    return parser
```

## Complete Example

```python
import argparse
import sys

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Running {args.input} -> {args.output}")
    
    process_file(args.input, args.output, args.count)

if __name__ == "__main__":
    main()
```

This pattern creates user-friendly, validated CLI tools.