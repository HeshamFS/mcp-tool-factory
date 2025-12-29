"""Tests for security scanner module."""

import tempfile
from pathlib import Path

import pytest
from tool_factory.security import (
    SecurityScanner,
    SecurityIssue,
    IssueSeverity,
    scan_code,
    scan_file,
)
from tool_factory.security.scanner import generate_security_report, ScanRule


class TestIssueSeverity:
    """Tests for IssueSeverity enum."""

    def test_severity_values(self):
        """Test severity values."""
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.CRITICAL.value == "critical"


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""

    def test_basic_issue(self):
        """Test basic issue creation."""
        issue = SecurityIssue(
            severity=IssueSeverity.HIGH,
            category="credentials",
            message="Hardcoded password",
            line_number=10,
            line_content='password = "secret123"',
            recommendation="Use environment variables",
        )
        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == "credentials"
        assert issue.line_number == 10

    def test_to_dict(self):
        """Test dictionary conversion."""
        issue = SecurityIssue(
            severity=IssueSeverity.CRITICAL,
            category="injection",
            message="SQL injection",
        )
        d = issue.to_dict()
        assert d["severity"] == "critical"
        assert d["category"] == "injection"
        assert d["message"] == "SQL injection"


class TestSecurityScanner:
    """Tests for SecurityScanner."""

    def test_default_rules(self):
        """Test scanner has default rules."""
        scanner = SecurityScanner()
        assert len(scanner.rules) > 0

    def test_custom_rules(self):
        """Test scanner with custom rules."""
        rules = [
            ScanRule(
                name="test_rule",
                category="test",
                severity=IssueSeverity.LOW,
                pattern=r"test_pattern",
                message="Test message",
                recommendation="Test recommendation",
            )
        ]
        scanner = SecurityScanner(rules)
        assert len(scanner.rules) == 1

    # Credential detection tests
    def test_detects_hardcoded_password(self):
        """Test detection of hardcoded passwords."""
        code = """
password = "supersecret123"
"""
        issues = scan_code(code)
        assert any(i.category == "credentials" for i in issues)
        assert any("password" in i.message.lower() for i in issues)

    def test_detects_hardcoded_api_key(self):
        """Test detection of hardcoded API keys."""
        code = """
api_key = "sk_test_FAKE_KEY_FOR_TESTING_ONLY_12345"
"""
        issues = scan_code(code)
        assert any("api key" in i.message.lower() for i in issues)

    def test_ignores_env_var_password(self):
        """Test ignores password from environment."""
        code = """
password = os.getenv("PASSWORD")
"""
        issues = scan_code(code)
        cred_issues = [i for i in issues if i.category == "credentials"]
        assert len(cred_issues) == 0

    # SQL injection tests
    def test_detects_sql_injection_fstring(self):
        """Test detection of SQL injection via f-string."""
        code = """
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
"""
        issues = scan_code(code)
        assert any("sql" in i.message.lower() for i in issues)

    def test_detects_sql_injection_concat(self):
        """Test detection of SQL injection via concatenation."""
        code = """
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
"""
        issues = scan_code(code)
        assert any("sql" in i.message.lower() for i in issues)

    # Command injection tests
    def test_detects_os_system(self):
        """Test detection of os.system()."""
        code = """
os.system("rm -rf " + user_input)
"""
        issues = scan_code(code)
        assert any("os.system" in i.message for i in issues)

    def test_detects_subprocess_shell_true(self):
        """Test detection of subprocess with shell=True."""
        code = """
subprocess.run(cmd, shell=True)
"""
        issues = scan_code(code)
        assert any("shell=True" in i.message for i in issues)

    def test_detects_eval(self):
        """Test detection of eval()."""
        code = """
result = eval(user_input)
"""
        issues = scan_code(code)
        assert any("eval" in i.message.lower() for i in issues)

    def test_detects_exec(self):
        """Test detection of exec()."""
        code = """
exec(code_string)
"""
        issues = scan_code(code)
        assert any("exec" in i.message.lower() for i in issues)

    def test_ignores_commented_eval(self):
        """Test ignores commented eval."""
        code = """
# eval(user_input) - don't use this
"""
        issues = scan_code(code)
        eval_issues = [i for i in issues if "eval" in i.message.lower()]
        assert len(eval_issues) == 0

    # Cryptography tests
    def test_detects_insecure_random(self):
        """Test detection of insecure random."""
        code = """
token = random.randint(0, 1000000)
"""
        issues = scan_code(code)
        assert any("random" in i.message.lower() for i in issues)

    def test_detects_weak_md5(self):
        """Test detection of MD5."""
        code = """
hash = hashlib.md5(data)
"""
        issues = scan_code(code)
        assert any("md5" in i.message.lower() for i in issues)

    def test_detects_weak_sha1(self):
        """Test detection of SHA-1."""
        code = """
hash = hashlib.sha1(data)
"""
        issues = scan_code(code)
        assert any(
            "sha-1" in i.message.lower() or "sha1" in i.message.lower() for i in issues
        )

    # Deserialization tests
    def test_detects_pickle_load(self):
        """Test detection of pickle.load()."""
        code = """
data = pickle.load(file)
"""
        issues = scan_code(code)
        assert any("pickle" in i.message.lower() for i in issues)

    def test_detects_unsafe_yaml(self):
        """Test detection of unsafe yaml.load()."""
        code = """
data = yaml.load(file)
"""
        issues = scan_code(code)
        assert any("yaml" in i.message.lower() for i in issues)

    # Configuration tests
    def test_detects_debug_true(self):
        """Test detection of debug=True."""
        code = """
DEBUG = True
"""
        issues = scan_code(code)
        assert any("debug" in i.message.lower() for i in issues)

    def test_detects_ssl_verify_false(self):
        """Test detection of verify=False."""
        code = """
requests.get(url, verify=False)
"""
        issues = scan_code(code)
        assert any("ssl" in i.message.lower() for i in issues)

    # File scanning
    def test_scan_file(self):
        """Test file scanning."""
        # Create temp file and close it before scanning (Windows compatibility)
        fd, temp_path = tempfile.mkstemp(suffix=".py")
        try:
            with open(fd, "w") as f:
                f.write('password = "secret123"\n')

            issues = scan_file(temp_path)
            assert len(issues) > 0
        finally:
            Path(temp_path).unlink()

    def test_scan_nonexistent_file(self):
        """Test scanning nonexistent file returns empty list."""
        issues = scan_file("/nonexistent/file.py")
        assert issues == []

    # Summary tests
    def test_get_summary(self):
        """Test summary generation."""
        scanner = SecurityScanner()
        issues = [
            SecurityIssue(IssueSeverity.CRITICAL, "credentials", "Hardcoded password"),
            SecurityIssue(IssueSeverity.HIGH, "injection", "SQL injection"),
            SecurityIssue(IssueSeverity.HIGH, "injection", "Command injection"),
            SecurityIssue(IssueSeverity.MEDIUM, "cryptography", "Weak hash"),
        ]

        summary = scanner.get_summary(issues)

        assert summary["total_issues"] == 4
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 2
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_category"]["injection"] == 2
        assert summary["has_critical"] is True


class TestGenerateSecurityReport:
    """Tests for generate_security_report function."""

    def test_no_issues(self):
        """Test report with no issues."""
        report = generate_security_report([])
        assert "No security issues" in report

    def test_report_with_issues(self):
        """Test report with issues."""
        issues = [
            SecurityIssue(
                severity=IssueSeverity.CRITICAL,
                category="credentials",
                message="Hardcoded password",
                line_number=5,
                line_content='password = "secret"',
                recommendation="Use environment variables",
            ),
        ]
        report = generate_security_report(issues)

        assert "SECURITY SCAN REPORT" in report
        assert "Total Issues: 1" in report
        assert "Critical: 1" in report
        assert "credentials" in report
        assert "Hardcoded password" in report
        assert "environment variables" in report

    def test_report_groups_by_severity(self):
        """Test report groups issues by severity."""
        issues = [
            SecurityIssue(IssueSeverity.LOW, "config", "Low issue"),
            SecurityIssue(IssueSeverity.CRITICAL, "credentials", "Critical issue"),
            SecurityIssue(IssueSeverity.MEDIUM, "crypto", "Medium issue"),
        ]
        report = generate_security_report(issues)

        # Critical should appear before Low
        critical_pos = report.find("[CRITICAL]")
        low_pos = report.find("[LOW]")
        assert critical_pos < low_pos


class TestScanCodeConvenience:
    """Tests for scan_code convenience function."""

    def test_scan_clean_code(self):
        """Test scanning clean code."""
        code = """
def add(a, b):
    return a + b
"""
        issues = scan_code(code)
        # Should have no or minimal issues
        critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        assert len(critical) == 0

    def test_scan_vulnerable_code(self):
        """Test scanning vulnerable code."""
        code = """
password = "admin123"
cursor.execute(f"SELECT * FROM users WHERE name = {name}")
os.system(command)
"""
        issues = scan_code(code)
        assert len(issues) >= 3  # At least password, SQL injection, command injection
