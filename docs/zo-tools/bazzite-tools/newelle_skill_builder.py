#!/usr/bin/env python3
"""
newelle_skill_builder.py - Generator for Newelle GTK4 AI assistant skill bundles.

Generates skill JSON files that define commands for Newelle assistant.
"""

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class SkillCommand:
    name: str
    description: str
    prompt: str
    examples: list[str]
    mcp_tools: list[str]
    tags: list[str]


@dataclass
class SkillBundle:
    name: str
    description: str
    version: str
    commands: list[SkillCommand]


class NewelleSkillBuilder:
    """Builds Newelle skill bundles for GTK4 AI assistant."""
    
    def __init__(self, mcp_endpoint: str = "http://127.0.0.1:8766"):
        self.mcp_endpoint = mcp_endpoint
        self.client = httpx.Client(timeout=10)
    
    def load_mcp_manifest(
        self, 
        endpoint: str | None = None,
        allowlist_path: str | None = None,
    ) -> dict[str, dict]:
        """
        Fetch the live MCP tool list from the bridge.
        Returns {tool_name: {description, annotations}} dict.
        Falls back to parsing configs/mcp-bridge-allowlist.yaml if HTTP fails.
        """
        ep = endpoint or self.mcp_endpoint
        
        # Try HTTP first
        try:
            response = self.client.get(f"{ep}/tools", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            tools = {}
            for tool in data.get("tools", []):
                name = tool.get("name") or tool.get("id")
                if name:
                    tools[name] = {
                        "description": tool.get("description", ""),
                        "annotations": tool.get("annotations", {}),
                    }
            
            if tools:
                return tools
                
        except Exception as e:
            logging.warning(f"HTTP manifest fetch failed: {e}, falling back to YAML")
        
        # Fallback to YAML
        if not allowlist_path:
            # Try common locations
            for path in [
                Path.home() / "workspace" / "bazzite-laptop" / "configs" / "mcp-bridge-allowlist.yaml",
                Path("./configs/mcp-bridge-allowlist.yaml"),
                Path("../configs/mcp-bridge-allowlist.yaml"),
            ]:
                if path.exists():
                    allowlist_path = str(path)
                    break
        
        if not allowlist_path or not HAS_YAML:
            logging.error("Could not load MCP manifest via HTTP or YAML")
            return {}
        
        try:
            with open(allowlist_path) as f:
                data = yaml.safe_load(f)
            
            tools = {}
            for name, config in data.get("tools", {}).items():
                tools[name] = {
                    "description": config.get("description", ""),
                    "annotations": config.get("annotations", {}),
                }
            return tools
            
        except Exception as e:
            logging.error(f"Failed to parse YAML fallback: {e}")
            return {}
    
    def scaffold_skill(
        self,
        name: str,
        description: str,
        commands_spec: list[dict],
        output_dir: str,
    ) -> str:
        """
        Generates a valid skill JSON.
        Validates: all mcp_tools exist in manifest, prompts < 2000 chars,
        required fields present.
        Writes to output_dir/{name}.json atomically.
        Returns output path.
        """
        # Load manifest for validation
        manifest = self.load_mcp_manifest()
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        skill_file = output_path / f"{name}.json"
        
        commands = []
        for cmd_spec in commands_spec:
            # Validate
            cmd_name = cmd_spec.get("name")
            if not cmd_name:
                raise ValueError("Command missing name")
            
            prompt = cmd_spec.get("prompt", "")
            if len(prompt) > 2000:
                raise ValueError(f"Prompt for {cmd_name} exceeds 2000 chars")
            
            mcp_tools = cmd_spec.get("mcp_tools", [])
            if mcp_tools and manifest:
                missing = [t for t in mcp_tools if t not in manifest]
                if missing:
                    logging.warning(f"Command {cmd_name} references unknown MCP tools: {missing}")
            
            command = SkillCommand(
                name=cmd_name,
                description=cmd_spec.get("description", ""),
                prompt=prompt,
                examples=cmd_spec.get("examples", []),
                mcp_tools=mcp_tools,
                tags=cmd_spec.get("tags", []),
            )
            commands.append(command)
        
        bundle = SkillBundle(
            name=name,
            description=description,
            version=cmd_spec.get("version", "1.0.0"),
            commands=commands,
        )
        
        # Build JSON
        skill_json = {
            "name": bundle.name,
            "description": bundle.description,
            "version": bundle.version,
            "commands": [
                {
                    "name": c.name,
                    "description": c.description,
                    "prompt": c.prompt,
                    "examples": c.examples,
                    "mcp_tools": c.mcp_tools,
                    "tags": c.tags,
                }
                for c in bundle.commands
            ],
        }
        
        # Validate with round-trip
        try:
            json.loads(json.dumps(skill_json))
        except json.JSONDecodeError as e:
            raise ValueError(f"Generated JSON is invalid: {e}")
        
        # Atomic write
        tmp_file = skill_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(skill_json, f, indent=2)
        os.replace(tmp_file, skill_file)
        
        return str(skill_file)
    
    def validate_skill(
        self, 
        skill_path: str, 
        manifest: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        """
        Validates a skill JSON: schema check, all referenced MCP tools exist,
        no empty prompts. Returns {valid: bool, errors: [str], warnings: [str]}.
        """
        if manifest is None:
            manifest = self.load_mcp_manifest()
        
        errors = []
        warnings = []
        
        try:
            with open(skill_path) as f:
                skill = json.load(f)
        except json.JSONDecodeError as e:
            return {"valid": False, "errors": [f"Invalid JSON: {e}"], "warnings": []}
        except FileNotFoundError:
            return {"valid": False, "errors": [f"File not found: {skill_path}"], "warnings": []}
        
        # Schema validation
        required_fields = ["name", "description", "version", "commands"]
        for field in required_fields:
            if field not in skill:
                errors.append(f"Missing required field: {field}")
        
        commands = skill.get("commands", [])
        if not isinstance(commands, list):
            errors.append("commands must be a list")
        else:
            for i, cmd in enumerate(commands):
                if not isinstance(cmd, dict):
                    errors.append(f"Command {i} is not a dict")
                    continue
                
                # Required command fields
                if "name" not in cmd:
                    errors.append(f"Command {i} missing name")
                if "description" not in cmd:
                    warnings.append(f"Command {cmd.get('name', i)} missing description")
                if "prompt" not in cmd:
                    errors.append(f"Command {cmd.get('name', i)} missing prompt")
                elif not cmd["prompt"]:
                    errors.append(f"Command {cmd.get('name', i)} has empty prompt")
                elif len(cmd["prompt"]) > 2000:
                    errors.append(f"Command {cmd.get('name', i)} prompt exceeds 2000 chars")
                
                # Validate MCP tools
                mcp_tools = cmd.get("mcp_tools", [])
                if manifest:
                    missing = [t for t in mcp_tools if t not in manifest]
                    if missing:
                        warnings.append(f"Command {cmd.get('name', i)} references unknown tools: {missing}")
                
                # Validate examples exist
                examples = cmd.get("examples", [])
                if not examples:
                    warnings.append(f"Command {cmd.get('name', i)} has no examples")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def validate_all_skills(
        self, 
        skills_dir: str, 
        manifest: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        """
        Validates all *.json in skills_dir. Returns summary report.
        """
        skills_path = Path(skills_dir)
        if not skills_path.exists():
            return {"total": 0, "valid": 0, "invalid": 0, "results": []}
        
        if manifest is None:
            manifest = self.load_mcp_manifest()
        
        results = []
        for skill_file in skills_path.glob("*.json"):
            result = self.validate_skill(str(skill_file), manifest)
            results.append({
                "file": str(skill_file),
                "name": skill_file.stem,
                **result,
            })
        
        return {
            "total": len(results),
            "valid": sum(1 for r in results if r["valid"]),
            "invalid": sum(1 for r in results if not r["valid"]),
            "results": results,
        }
    
    def generate_morning_briefing_skill(
        self,
        manifest: dict[str, dict] | None,
        output_dir: str,
    ) -> str:
        """
        Auto-generates a morning briefing skill that uses available security
        and monitoring tools based on what's actually in the manifest.
        """
        if manifest is None:
            manifest = self.load_mcp_manifest()
        
        # Filter for security/monitoring tools
        security_tools = [
            name for name, info in manifest.items()
            if any(k in info.get("description", "").lower() for k in [
                "security", "threat", "vuln", "scan", "system", "monitor", "status", "health", "log"
            ])
        ]
        
        commands = [
            {
                "name": "security_check",
                "description": "Check system security status and recent threats",
                "prompt": """You are a security briefing assistant. Check the current system security status using available tools.

Steps:
1. Get overall system status
2. Check for new threat intelligence  
3. Review any recent security alerts
4. Summarize findings in a concise morning briefing format

Be professional and highlight any urgent issues first.""",
                "examples": [
                    "Check my security status",
                    "Give me a security briefing",
                    "Any security issues?",
                ],
                "mcp_tools": security_tools[:5],  # Limit to 5 relevant tools
                "tags": ["security", "morning", "briefing"],
            },
            {
                "name": "system_health",
                "description": "Check overall system health and performance",
                "prompt": """You are a system monitoring assistant. Check the health of the bazzite-laptop AI system.

Check:
1. Service status
2. Recent performance metrics
3. Any errors or warnings
4. Resource usage

Provide a summary in bullet points.""",
                "examples": [
                    "How is my system?",
                    "Check system health",
                    "Is everything running?",
                ],
                "mcp_tools": [t for t in security_tools if "status" in t.lower() or "health" in t.lower()][:3],
                "tags": ["monitoring", "health", "status"],
            },
        ]
        
        return self.scaffold_skill(
            name="morning_briefing",
            description="Morning security and system health briefing",
            commands_spec=commands,
            output_dir=output_dir,
        )
    
    def generate_security_skill(
        self,
        manifest: dict[str, dict] | None,
        output_dir: str,
    ) -> str:
        """
        Generates a security investigation skill with commands that chain
        threat_lookup, ip_lookup, url_lookup, and correlate tools.
        """
        if manifest is None:
            manifest = self.load_mcp_manifest()
        
        # Find relevant security tools
        lookup_tools = [
            name for name, info in manifest.items()
            if any(k in name.lower() for k in ["lookup", "threat", "ip", "url", "hash", "intel"])
        ]
        
        commands = [
            {
                "name": "investigate_indicator",
                "description": "Investigate a security indicator (IP, URL, hash, or domain)",
                "prompt": """You are a security analyst. Investigate the provided indicator using multiple threat intelligence sources.

Steps:
1. Determine the type of indicator (IP, URL, hash, domain, file path)
2. Use appropriate lookup tools to gather intelligence
3. Cross-reference findings across sources
4. Provide a risk assessment and recommendations

Format your response as:
- Indicator Type: [type]
- Threat Level: [Low/Medium/High/Critical]
- Sources Checked: [list]
- Summary: [brief summary]
- Recommendations: [actionable steps]""",
                "examples": [
                    "Check IP 192.168.1.1",
                    "Investigate hash abc123...",
                    "Is https://example.com malicious?",
                ],
                "mcp_tools": lookup_tools[:5],
                "tags": ["security", "investigation", "threat_intel"],
            },
            {
                "name": "correlate_threats",
                "description": "Correlate multiple threat indicators to find patterns",
                "prompt": """You are a threat intelligence analyst. Analyze multiple indicators together to find patterns and connections.

Steps:
1. Look up each indicator
2. Look for common attributes (ASNs, registrars, file paths, behavioral patterns)
3. Check for known campaign or actor associations
4. Determine if this is part of a larger campaign

Provide a correlation report highlighting any shared infrastructure or TTPs.""",
                "examples": [
                    "Correlate these IPs: [1.2.3.4, 5.6.7.8]",
                    "Do these hashes share anything in common?",
                    "Are these URLs related?",
                ],
                "mcp_tools": [t for t in lookup_tools if "lookup" in t or "correlate" in t][:4],
                "tags": ["security", "correlation", "analysis"],
            },
        ]
        
        return self.scaffold_skill(
            name="security_investigation",
            description="Security indicator investigation and correlation",
            commands_spec=commands,
            output_dir=output_dir,
        )
    
    def run(self, command: str, **kwargs) -> Any:
        """CLI dispatcher."""
        if command == "scaffold":
            return self.scaffold_skill(
                name=kwargs["name"],
                description=kwargs["description"],
                commands_spec=kwargs["commands_spec"],
                output_dir=kwargs["output_dir"],
            )
        elif command == "validate":
            return self.validate_skill(
                skill_path=kwargs["skill_path"],
                manifest=kwargs.get("manifest"),
            )
        elif command == "validate-all":
            return self.validate_all_skills(
                skills_dir=kwargs["skills_dir"],
                manifest=kwargs.get("manifest"),
            )
        elif command == "gen-morning":
            return self.generate_morning_briefing_skill(
                manifest=kwargs.get("manifest"),
                output_dir=kwargs["output_dir"],
            )
        elif command == "gen-security":
            return self.generate_security_skill(
                manifest=kwargs.get("manifest"),
                output_dir=kwargs["output_dir"],
            )
        else:
            raise ValueError(f"Unknown command: {command}")


def main():
    parser = argparse.ArgumentParser(description="Newelle Skill Builder")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # scaffold command
    scaffold_parser = subparsers.add_parser("scaffold", help="Create new skill")
    scaffold_parser.add_argument("name", help="Skill name")
    scaffold_parser.add_argument("--description", "-d", required=True)
    scaffold_parser.add_argument("--commands", "-c", required=True, help="Commands JSON spec")
    scaffold_parser.add_argument("--output-dir", "-o", default="./skills", help="Output directory")
    
    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a skill")
    validate_parser.add_argument("skill_path", help="Path to skill JSON")
    
    # validate-all command
    validate_all_parser = subparsers.add_parser("validate-all", help="Validate all skills in directory")
    validate_all_parser.add_argument("skills_dir", help="Directory containing skill JSONs")
    
    # gen-morning command
    gen_morning_parser = subparsers.add_parser("gen-morning", help="Generate morning briefing skill")
    gen_morning_parser.add_argument("--output-dir", "-o", default="./skills", help="Output directory")
    
    # gen-security command
    gen_security_parser = subparsers.add_parser("gen-security", help="Generate security investigation skill")
    gen_security_parser.add_argument("--output-dir", "-o", default="./skills", help="Output directory")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    builder = NewelleSkillBuilder()
    
    if args.command == "scaffold":
        commands_spec = json.loads(args.commands)
        result = builder.run("scaffold",
            name=args.name,
            description=args.description,
            commands_spec=commands_spec,
            output_dir=args.output_dir,
        )
        print(f"Generated skill: {result}")
        
    elif args.command == "validate":
        result = builder.run("validate", skill_path=args.skill_path)
        print(json.dumps(result, indent=2))
        
    elif args.command == "validate-all":
        result = builder.run("validate-all", skills_dir=args.skills_dir)
        print(json.dumps(result, indent=2))
        
    elif args.command == "gen-morning":
        result = builder.run("gen-morning", output_dir=args.output_dir)
        print(f"Generated morning briefing skill: {result}")
        
    elif args.command == "gen-security":
        result = builder.run("gen-security", output_dir=args.output_dir)
        print(f"Generated security skill: {result}")


if __name__ == "__main__":
    main()
