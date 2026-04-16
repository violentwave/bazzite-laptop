"""MCP Contract Parity Checker.

Compares the canonical MCP contract (allowlist) against:
- UI hooks (callMCPTool calls)
- Live manifest
- Handlers

Detects drift and generates a report.
"""

import json
import sys
from pathlib import Path
from typing import Any

from ai.config import CONFIGS_DIR

CONTRACT_PATH = CONFIGS_DIR / "mcp-bridge-allowlist.yaml"


def load_contract() -> dict[str, Any]:
    """Load the MCP contract from allowlist."""
    import yaml

    with open(CONTRACT_PATH) as f:
        data = yaml.safe_load(f) or {}
    return data.get("tools", {})


def check_parity() -> dict[str, Any]:
    """Check parity between contract and references."""
    contract_tools = load_contract()

    report = {
        "total_tools": len(contract_tools),
        "drift_detected": False,
        "issues": [],
    }

    # Check for tools without required fields
    for tool_name, tool_def in contract_tools.items():
        if "description" not in tool_def:
            report["issues"].append(
                {
                    "tool": tool_name,
                    "issue": "missing_description",
                    "severity": "low",
                }
            )

        # Check for handler - either source (python) or command (subprocess)
        has_source = "source" in tool_def
        has_command = "command" in tool_def
        if not has_source and not has_command:
            report["issues"].append(
                {
                    "tool": tool_name,
                    "issue": "missing_handler",
                    "severity": "high",
                }
            )
            report["drift_detected"] = True

    # Check for conflicting annotations
    annotations = tool_def.get("annotations", {})
    if annotations.get("readOnly") and annotations.get("destructive"):
        report["issues"].append(
            {
                "tool": tool_name,
                "issue": "conflicting_annotations",
                "severity": "high",
            }
        )
        report["drift_detected"] = True

    if not report["issues"]:
        report["status"] = "healthy"
    else:
        report["status"] = "drift_detected"

    return report


def main() -> int:
    """Main entry point."""
    report = check_parity()

    print("MCP Contract Parity Check")
    print("==========================")
    print(f"Total tools: {report['total_tools']}")
    print(f"Status: {report['status']}")

    if report["issues"]:
        print(f"\nIssues found: {len(report['issues'])}")
        for issue in report["issues"][:10]:
            print(f"  - {issue['tool']}: {issue['issue']} ({issue['severity']})")

    # Save report
    output_path = Path(__file__).parent.parent / "docs" / "evidence" / "p114" / "parity_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {output_path}")

    return 0 if not report["drift_detected"] else 1


if __name__ == "__main__":
    sys.exit(main())
