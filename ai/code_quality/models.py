"""Data models for the code quality pipeline."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Lint finding severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintFinding:
    """A single lint finding from any linter."""
    tool: str           # "ruff", "bandit", "shellcheck"
    file: str           # path to the file
    line: int           # line number
    code: str           # rule code e.g. "E501", "B101", "SC2086"
    message: str        # human-readable description
    severity: Severity = Severity.WARNING
    column: int = 0
    end_line: int | None = None
    fix_suggestion: str = ""   # AI-generated fix (populated by analyzer)


@dataclass
class LintSummary:
    """Aggregated summary for a lint run."""
    tool: str
    findings: list[LintFinding] = field(default_factory=list)
    exit_code: int = 0
    runtime_seconds: float = 0.0
    error_message: str = ""  # stderr if tool failed to run

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    @property
    def total_count(self) -> int:
        return len(self.findings)
