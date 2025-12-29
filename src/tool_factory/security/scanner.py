"""Security scanner for generated MCP server code.

Scans for common security issues including:
- Hardcoded credentials
- SQL injection patterns
- Command injection patterns
- Path traversal vulnerabilities
- Insecure randomness
- Missing input validation
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class IssueSeverity(Enum):
    """Severity levels for security issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityIssue:
    """A detected security issue."""

    severity: IssueSeverity
    category: str
    message: str
    line_number: int | None = None
    line_content: str | None = None
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "recommendation": self.recommendation,
        }


@dataclass
class ScanRule:
    """A security scanning rule."""

    name: str
    category: str
    severity: IssueSeverity
    pattern: str
    message: str
    recommendation: str
    exclude_patterns: list[str] = field(default_factory=list)


class SecurityScanner:
    """Scans code for security vulnerabilities."""

    # Default scanning rules
    DEFAULT_RULES = [
        # Hardcoded credentials
        ScanRule(
            name="hardcoded_password",
            category="credentials",
            severity=IssueSeverity.CRITICAL,
            pattern=r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            message="Hardcoded password detected",
            recommendation="Use environment variables or a secrets manager",
            exclude_patterns=[r'password\s*=\s*["\'][\$\{]', r"getenv"],
        ),
        ScanRule(
            name="hardcoded_api_key",
            category="credentials",
            severity=IssueSeverity.CRITICAL,
            pattern=r'(?i)(api[_-]?key|apikey|secret[_-]?key)\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            message="Hardcoded API key detected",
            recommendation="Use environment variables or a secrets manager",
            exclude_patterns=[r"os\.environ", r"getenv"],
        ),
        ScanRule(
            name="hardcoded_token",
            category="credentials",
            severity=IssueSeverity.HIGH,
            pattern=r'(?i)(token|bearer|auth)\s*=\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            message="Hardcoded token detected",
            recommendation="Use environment variables or a secrets manager",
            exclude_patterns=[r"os\.environ", r"getenv", r"placeholder"],
        ),
        # SQL injection
        ScanRule(
            name="sql_injection_format",
            category="injection",
            severity=IssueSeverity.CRITICAL,
            pattern=r'(?i)(execute|cursor\.execute)\s*\(\s*f["\'].*\{.*\}',
            message="Potential SQL injection via f-string",
            recommendation="Use parameterized queries instead",
        ),
        ScanRule(
            name="sql_injection_concat",
            category="injection",
            severity=IssueSeverity.CRITICAL,
            pattern=r"(?i)(execute|cursor\.execute)\s*\([^)]*\+\s*[^)]+\)",
            message="Potential SQL injection via string concatenation",
            recommendation="Use parameterized queries instead",
        ),
        ScanRule(
            name="sql_injection_percent",
            category="injection",
            severity=IssueSeverity.HIGH,
            pattern=r'(?i)(execute|cursor\.execute)\s*\(\s*["\'].*%s.*["\'].*%',
            message="Potential SQL injection via % formatting",
            recommendation="Use parameterized queries with proper escaping",
        ),
        # Command injection
        ScanRule(
            name="command_injection_os",
            category="injection",
            severity=IssueSeverity.CRITICAL,
            pattern=r"os\.system\s*\(",
            message="os.system() is vulnerable to command injection",
            recommendation="Use subprocess.run() with shell=False",
        ),
        ScanRule(
            name="command_injection_popen",
            category="injection",
            severity=IssueSeverity.HIGH,
            pattern=r"os\.popen\s*\(",
            message="os.popen() is vulnerable to command injection",
            recommendation="Use subprocess.run() with shell=False",
        ),
        ScanRule(
            name="command_injection_shell",
            category="injection",
            severity=IssueSeverity.HIGH,
            pattern=r"subprocess\.[^(]+\([^)]*shell\s*=\s*True",
            message="subprocess with shell=True is vulnerable to injection",
            recommendation="Use shell=False with a list of arguments",
        ),
        ScanRule(
            name="command_injection_eval",
            category="injection",
            severity=IssueSeverity.CRITICAL,
            pattern=r"(?<!#\s)eval\s*\(",
            message="eval() is dangerous and can execute arbitrary code",
            recommendation="Avoid eval(); use ast.literal_eval() for safe evaluation",
        ),
        ScanRule(
            name="command_injection_exec",
            category="injection",
            severity=IssueSeverity.CRITICAL,
            pattern=r"(?<!#\s)exec\s*\(",
            message="exec() is dangerous and can execute arbitrary code",
            recommendation="Avoid exec(); find safer alternatives",
        ),
        # Path traversal
        ScanRule(
            name="path_traversal",
            category="path_traversal",
            severity=IssueSeverity.HIGH,
            pattern=r"open\s*\([^)]*\+\s*[^)]+\)",
            message="Potential path traversal via string concatenation in file path",
            recommendation="Validate and sanitize file paths; use pathlib",
        ),
        # Insecure randomness
        ScanRule(
            name="insecure_random",
            category="cryptography",
            severity=IssueSeverity.MEDIUM,
            pattern=r"(?<!secrets\.)random\.(random|randint|choice|shuffle)",
            message="Using random module for potentially security-sensitive operation",
            recommendation="Use secrets module for security-sensitive randomness",
        ),
        # Weak hashing
        ScanRule(
            name="weak_hash_md5",
            category="cryptography",
            severity=IssueSeverity.MEDIUM,
            pattern=r"hashlib\.md5\s*\(",
            message="MD5 is cryptographically weak",
            recommendation="Use SHA-256 or stronger for security purposes",
        ),
        ScanRule(
            name="weak_hash_sha1",
            category="cryptography",
            severity=IssueSeverity.MEDIUM,
            pattern=r"hashlib\.sha1\s*\(",
            message="SHA-1 is cryptographically weak",
            recommendation="Use SHA-256 or stronger for security purposes",
        ),
        # Insecure deserialization
        ScanRule(
            name="pickle_load",
            category="deserialization",
            severity=IssueSeverity.HIGH,
            pattern=r"pickle\.load[s]?\s*\(",
            message="Pickle deserialization can execute arbitrary code",
            recommendation="Use JSON or other safe serialization formats",
        ),
        ScanRule(
            name="yaml_load",
            category="deserialization",
            severity=IssueSeverity.HIGH,
            pattern=r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader\s*=\s*yaml\.SafeLoader)",
            message="yaml.load() without SafeLoader can execute arbitrary code",
            recommendation="Use yaml.safe_load() or specify Loader=yaml.SafeLoader",
        ),
        # Debugging/development code
        ScanRule(
            name="debug_true",
            category="configuration",
            severity=IssueSeverity.MEDIUM,
            pattern=r"(?i)debug\s*=\s*True",
            message="Debug mode enabled",
            recommendation="Ensure debug is disabled in production",
        ),
        ScanRule(
            name="print_secrets",
            category="logging",
            severity=IssueSeverity.MEDIUM,
            pattern=r"print\s*\([^)]*(?:password|secret|token|key)[^)]*\)",
            message="Potentially logging sensitive information",
            recommendation="Avoid logging sensitive data; use proper secret handling",
        ),
        # Insecure SSL/TLS
        ScanRule(
            name="ssl_verify_false",
            category="network",
            severity=IssueSeverity.HIGH,
            pattern=r"verify\s*=\s*False",
            message="SSL verification disabled",
            recommendation="Enable SSL verification in production",
        ),
        # Hardcoded IPs/URLs
        ScanRule(
            name="hardcoded_ip",
            category="configuration",
            severity=IssueSeverity.LOW,
            pattern=r'["\'](?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)["\']',
            message="Hardcoded IP address detected",
            recommendation="Use configuration or environment variables",
            exclude_patterns=[r"127\.0\.0\.1", r"0\.0\.0\.0", r"localhost"],
        ),
    ]

    def __init__(self, rules: list[ScanRule] | None = None):
        """Initialize scanner with rules.

        Args:
            rules: Custom rules (uses defaults if None)
        """
        self.rules = rules if rules is not None else self.DEFAULT_RULES

    def scan(self, code: str) -> list[SecurityIssue]:
        """Scan code for security issues.

        Args:
            code: Source code to scan

        Returns:
            List of detected security issues
        """
        issues = []
        lines = code.split("\n")

        for rule in self.rules:
            pattern = re.compile(rule.pattern)

            for line_num, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                if pattern.search(line):
                    # Check exclusion patterns
                    excluded = False
                    for exclude in rule.exclude_patterns:
                        if re.search(exclude, line):
                            excluded = True
                            break

                    if not excluded:
                        issues.append(
                            SecurityIssue(
                                severity=rule.severity,
                                category=rule.category,
                                message=rule.message,
                                line_number=line_num,
                                line_content=line.strip()[:100],
                                recommendation=rule.recommendation,
                            )
                        )

        return issues

    def scan_file(self, file_path: str | Path) -> list[SecurityIssue]:
        """Scan a file for security issues.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of detected security issues
        """
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            code = path.read_text(encoding="utf-8")
            return self.scan(code)
        except Exception:
            return []

    def get_summary(self, issues: list[SecurityIssue]) -> dict[str, Any]:
        """Get summary of scan results.

        Args:
            issues: List of security issues

        Returns:
            Summary dictionary
        """
        severity_counts = {s: 0 for s in IssueSeverity}
        category_counts: dict[str, int] = {}

        for issue in issues:
            severity_counts[issue.severity] += 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        return {
            "total_issues": len(issues),
            "by_severity": {s.value: c for s, c in severity_counts.items()},
            "by_category": category_counts,
            "has_critical": severity_counts[IssueSeverity.CRITICAL] > 0,
            "has_high": severity_counts[IssueSeverity.HIGH] > 0,
        }


def scan_code(code: str) -> list[SecurityIssue]:
    """Scan code for security issues.

    Args:
        code: Source code to scan

    Returns:
        List of detected security issues
    """
    scanner = SecurityScanner()
    return scanner.scan(code)


def scan_file(file_path: str | Path) -> list[SecurityIssue]:
    """Scan a file for security issues.

    Args:
        file_path: Path to the file to scan

    Returns:
        List of detected security issues
    """
    scanner = SecurityScanner()
    return scanner.scan_file(file_path)


def generate_security_report(issues: list[SecurityIssue]) -> str:
    """Generate a security report from scan results.

    Args:
        issues: List of security issues

    Returns:
        Formatted report string
    """
    if not issues:
        return "No security issues detected."

    scanner = SecurityScanner()
    summary = scanner.get_summary(issues)

    lines = [
        "=" * 60,
        "SECURITY SCAN REPORT",
        "=" * 60,
        "",
        f"Total Issues: {summary['total_issues']}",
        f"  Critical: {summary['by_severity']['critical']}",
        f"  High: {summary['by_severity']['high']}",
        f"  Medium: {summary['by_severity']['medium']}",
        f"  Low: {summary['by_severity']['low']}",
        "",
        "-" * 60,
        "ISSUES BY CATEGORY",
        "-" * 60,
    ]

    for category, count in sorted(summary["by_category"].items()):
        lines.append(f"  {category}: {count}")

    lines.extend(
        [
            "",
            "-" * 60,
            "DETAILED FINDINGS",
            "-" * 60,
        ]
    )

    # Group by severity
    for severity in [
        IssueSeverity.CRITICAL,
        IssueSeverity.HIGH,
        IssueSeverity.MEDIUM,
        IssueSeverity.LOW,
    ]:
        severity_issues = [i for i in issues if i.severity == severity]
        if severity_issues:
            lines.append(f"\n[{severity.value.upper()}]")
            for issue in severity_issues:
                lines.append(f"  Line {issue.line_number}: {issue.message}")
                if issue.line_content:
                    lines.append(f"    Code: {issue.line_content}")
                if issue.recommendation:
                    lines.append(f"    Fix: {issue.recommendation}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
