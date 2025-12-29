"""Tests for CLI module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from click.testing import CliRunner

from tool_factory.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCliGroup:
    """Tests for main CLI group."""

    def test_cli_help(self, runner):
        """Test CLI shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "MCP Tool Factory" in result.output

    def test_cli_version(self, runner):
        """Test CLI shows version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestGenerateCommand:
    """Tests for generate command."""

    def test_generate_help(self, runner):
        """Test generate command shows help."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "DESCRIPTION" in result.output
        assert "--output" in result.output
        assert "--provider" in result.output

    def test_generate_shows_provider_choices(self, runner):
        """Test generate shows valid provider choices."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert "claude_code" in result.output
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "google" in result.output


class TestFromOpenAPICommand:
    """Tests for from-openapi command."""

    def test_from_openapi_help(self, runner):
        """Test from-openapi command shows help."""
        result = runner.invoke(cli, ["from-openapi", "--help"])
        assert result.exit_code == 0
        assert "OPENAPI_PATH" in result.output
        assert "--base-url" in result.output

    def test_from_openapi_missing_file(self, runner):
        """Test from-openapi with missing file."""
        result = runner.invoke(cli, ["from-openapi", "nonexistent.yaml"])
        assert result.exit_code != 0


class TestFromDatabaseCommand:
    """Tests for from-database command."""

    def test_from_database_help(self, runner):
        """Test from-database command shows help."""
        result = runner.invoke(cli, ["from-database", "--help"])
        assert result.exit_code == 0
        assert "DATABASE_PATH" in result.output
        assert "--type" in result.output

    def test_from_database_shows_type_choices(self, runner):
        """Test from-database shows valid type choices."""
        result = runner.invoke(cli, ["from-database", "--help"])
        assert "sqlite" in result.output
        assert "postgresql" in result.output


class TestTestCommand:
    """Tests for test command."""

    def test_test_help(self, runner):
        """Test test command shows help."""
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        assert "SERVER_PATH" in result.output


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_help(self, runner):
        """Test serve command shows help."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "SERVER_PATH" in result.output
        assert "--transport" in result.output
        assert "--port" in result.output

    def test_serve_shows_transport_choices(self, runner):
        """Test serve shows valid transport choices."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert "stdio" in result.output
        assert "sse" in result.output


class TestInfoCommand:
    """Tests for info command."""

    def test_info_basic(self, runner):
        """Test info command shows information."""
        result = runner.invoke(cli, ["info"])

        assert result.exit_code == 0
        assert "MCP Tool Factory" in result.output

    def test_info_shows_supported_platforms(self, runner):
        """Test info shows supported platforms."""
        result = runner.invoke(cli, ["info"])

        assert "Claude" in result.output
        assert "OpenAI" in result.output
        assert "Google" in result.output
        assert "LangChain" in result.output

    def test_info_shows_commands(self, runner):
        """Test info shows available commands."""
        result = runner.invoke(cli, ["info"])

        assert "generate" in result.output
        assert "from-openapi" in result.output
        assert "from-database" in result.output
