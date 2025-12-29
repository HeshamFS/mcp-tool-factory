"""Comprehensive tests for CLI module to increase coverage."""

import json
import os

import pytest
from click.testing import CliRunner

from tool_factory.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIHelp:
    """Tests for CLI help and version."""

    def test_cli_help(self, runner):
        """Test that help shows available commands."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "from-openapi" in result.output
        assert "from-database" in result.output

    def test_cli_version(self, runner):
        """Test that version option works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestGenerateCommandHelp:
    """Tests for generate command options."""

    def test_generate_help(self, runner):
        """Test generate command help."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--name" in result.output
        assert "--provider" in result.output
        assert "--model" in result.output
        assert "--web-search" in result.output
        assert "--auth" in result.output
        assert "--health-check" in result.output
        assert "--logging" in result.output
        assert "--metrics" in result.output
        assert "--rate-limit" in result.output
        assert "--retries" in result.output

    def test_generate_requires_description(self, runner):
        """Test generate requires description argument."""
        result = runner.invoke(cli, ["generate"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestFromOpenAPICommandHelp:
    """Tests for from-openapi command options."""

    def test_from_openapi_help(self, runner):
        """Test from-openapi command help."""
        result = runner.invoke(cli, ["from-openapi", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--name" in result.output
        assert "--base-url" in result.output

    def test_from_openapi_requires_spec(self, runner):
        """Test from-openapi requires spec file argument."""
        result = runner.invoke(cli, ["from-openapi"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestFromDatabaseCommandHelp:
    """Tests for from-database command options."""

    def test_from_database_help(self, runner):
        """Test from-database command help."""
        result = runner.invoke(cli, ["from-database", "--help"])
        assert result.exit_code == 0
        assert "DATABASE" in result.output
        assert "--output" in result.output
        assert "--name" in result.output
        assert "--tables" in result.output
        assert "--type" in result.output

    def test_from_database_requires_database(self, runner):
        """Test from-database requires database argument."""
        result = runner.invoke(cli, ["from-database"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestServeCommandHelp:
    """Tests for serve command options."""

    def test_serve_help(self, runner):
        """Test serve command help."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--transport" in result.output
        assert "--port" in result.output

    def test_serve_requires_directory(self, runner):
        """Test serve requires server directory argument."""
        result = runner.invoke(cli, ["serve"])
        assert result.exit_code != 0


class TestTestCommandHelp:
    """Tests for test command options."""

    def test_test_help(self, runner):
        """Test test command help."""
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        # Just check that help text displays
        assert "Usage:" in result.output


class TestInfoCommandHelp:
    """Tests for info command options."""

    def test_info_help(self, runner):
        """Test info command help."""
        result = runner.invoke(cli, ["info", "--help"])
        assert result.exit_code == 0
        # Info command shows factory information
        assert "Show information" in result.output


class TestProviderChoices:
    """Tests for provider option validation."""

    def test_generate_invalid_provider(self, runner):
        """Test that invalid provider is rejected."""
        result = runner.invoke(cli, ["generate", "test", "--provider", "invalid"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_generate_valid_providers(self, runner):
        """Test that all valid providers are accepted (help text)."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert "claude_code" in result.output
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "google" in result.output


class TestTransportChoices:
    """Tests for transport option validation."""

    def test_serve_transport_choices(self, runner):
        """Test that transport options are documented."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert "stdio" in result.output
        assert "sse" in result.output


class TestDatabaseTypeChoices:
    """Tests for database type option validation."""

    def test_database_type_choices(self, runner):
        """Test that database type options are documented."""
        result = runner.invoke(cli, ["from-database", "--help"])
        assert "sqlite" in result.output
        assert "postgresql" in result.output


class TestCLIOutputOptions:
    """Tests for output directory options."""

    def test_generate_default_output(self, runner):
        """Test generate has default output directory."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert "./servers" in result.output

    def test_from_openapi_default_output(self, runner):
        """Test from-openapi has default output directory."""
        result = runner.invoke(cli, ["from-openapi", "--help"])
        assert "./servers" in result.output


class TestCLIFlagOptions:
    """Tests for flag options."""

    def test_generate_flag_defaults(self, runner):
        """Test generate flag options defaults in help."""
        result = runner.invoke(cli, ["generate", "--help"])
        # Check that toggle options are documented
        assert "health-check" in result.output
        assert "logging" in result.output
        assert "metrics" in result.output
        assert "retries" in result.output


class TestInfoCommand:
    """Tests for info command functionality."""

    def test_info_shows_version(self, runner):
        """Test info command shows version."""
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "MCP Tool Factory" in result.output

    def test_info_shows_commands(self, runner):
        """Test info shows available commands."""
        result = runner.invoke(cli, ["info"])
        assert "generate" in result.output
        assert "from-openapi" in result.output
        assert "from-database" in result.output

    def test_info_shows_features(self, runner):
        """Test info shows features."""
        result = runner.invoke(cli, ["info"])
        assert "Claude" in result.output or "claude" in result.output.lower()
        assert "OpenAI" in result.output or "openai" in result.output.lower()


class TestGenerateMocked:
    """Tests for generate command with mocked agent."""

    def test_generate_with_mocked_agent(self, runner):
        """Test generate command with mocked ToolFactoryAgent."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="test_tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Create test tool",
                        "--name",
                        "TestServer",
                        "--output",
                        "./output",
                    ],
                )

                # Agent should be called
                mock_agent.generate_from_description_sync.assert_called_once()

    def test_generate_with_web_search_flag(self, runner):
        """Test generate with web search enabled."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Weather API tool",
                        "--web-search",
                        "--output",
                        "./output",
                    ],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                assert call_kwargs.get("web_search") is True

    def test_generate_with_auth_vars(self, runner):
        """Test generate with auth environment variables."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "API tool",
                        "--auth",
                        "API_KEY",
                        "--auth",
                        "SECRET",
                        "--output",
                        "./output",
                    ],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                auth_vars = call_kwargs.get("auth_env_vars", [])
                assert "API_KEY" in auth_vars
                assert "SECRET" in auth_vars

    def test_generate_with_production_options(self, runner):
        """Test generate with production options."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--metrics",
                        "--rate-limit",
                        "100",
                        "--output",
                        "./output",
                    ],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                prod_config = call_kwargs.get("production_config")
                assert prod_config is not None
                assert prod_config.enable_metrics is True
                assert prod_config.enable_rate_limiting is True

    def test_generate_no_health_check(self, runner):
        """Test generate without health check."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--no-health-check",
                        "--output",
                        "./output",
                    ],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                assert call_kwargs.get("include_health_check") is False

    def test_generate_with_explicit_provider(self, runner):
        """Test generate with explicit provider."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--provider",
                        "openai",
                        "--output",
                        "./output",
                    ],
                )

                mock_agent.generate_from_description_sync.assert_called_once()

    def test_generate_with_custom_model(self, runner):
        """Test generate with custom model."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--provider",
                        "anthropic",
                        "--model",
                        "claude-3-5-sonnet-20241022",
                        "--output",
                        "./output",
                    ],
                )

                mock_agent.generate_from_description_sync.assert_called_once()

    def test_generate_with_execution_log(self, runner):
        """Test generate shows execution log info."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = Mock()  # Non-None execution log
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                result = runner.invoke(
                    cli, ["generate", "Test tool", "--output", "./output"]
                )

                # Should mention execution log
                assert (
                    "EXECUTION_LOG" in result.output
                    or "execution" in result.output.lower()
                )

    def test_generate_no_logging_flag(self, runner):
        """Test generate with no-logging flag."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    ["generate", "Test tool", "--no-logging", "--output", "./output"],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                prod_config = call_kwargs.get("production_config")
                assert prod_config.enable_logging is False

    def test_generate_no_retries_flag(self, runner):
        """Test generate with no-retries flag."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    ["generate", "Test tool", "--no-retries", "--output", "./output"],
                )

                call_kwargs = mock_agent.generate_from_description_sync.call_args.kwargs
                prod_config = call_kwargs.get("production_config")
                assert prod_config.enable_retries is False


class TestFromOpenAPIMocked:
    """Tests for from-openapi command with mocked agent."""

    def test_from_openapi_json_spec(self, runner):
        """Test from-openapi with JSON spec."""
        from unittest.mock import Mock, patch

        mock_parser = Mock()
        mock_parser.get_info.return_value = {"title": "Test API", "version": "1.0"}
        mock_parser.get_servers.return_value = [{"url": "https://api.example.com"}]
        mock_auth = Mock()
        mock_auth.auth_type = Mock(value="none")
        mock_parser.get_auth_config.return_value = mock_auth

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="get_users")]
        mock_agent.generate_from_openapi = Mock(return_value=mock_result)

        with patch("tool_factory.openapi.OpenAPIParser", return_value=mock_parser):
            with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
                with runner.isolated_filesystem():
                    spec = {
                        "openapi": "3.0.0",
                        "info": {"title": "Test", "version": "1.0"},
                    }
                    with open("spec.json", "w") as f:
                        json.dump(spec, f)

                    runner.invoke(
                        cli, ["from-openapi", "spec.json", "--output", "./output"]
                    )

                    mock_parser.get_info.assert_called()

    def test_from_openapi_yaml_spec(self, runner):
        """Test from-openapi with YAML spec."""
        from unittest.mock import Mock, patch

        mock_parser = Mock()
        mock_parser.get_info.return_value = {"title": "API", "version": "1.0"}
        mock_parser.get_servers.return_value = []
        mock_auth = Mock()
        mock_auth.auth_type = Mock(value="api_key")
        mock_auth.env_var_name = "API_KEY"
        mock_parser.get_auth_config.return_value = mock_auth

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool")]
        mock_agent.generate_from_openapi = Mock(return_value=mock_result)

        with patch("tool_factory.openapi.OpenAPIParser", return_value=mock_parser):
            with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
                with runner.isolated_filesystem():
                    with open("spec.yaml", "w") as f:
                        f.write(
                            "openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'"
                        )

                    runner.invoke(
                        cli,
                        [
                            "from-openapi",
                            "spec.yaml",
                            "--name",
                            "CustomServer",
                            "--output",
                            "./output",
                        ],
                    )

                    mock_parser.get_info.assert_called()

    def test_from_openapi_with_base_url(self, runner):
        """Test from-openapi with custom base URL."""
        from unittest.mock import Mock, patch

        mock_parser = Mock()
        mock_parser.get_info.return_value = {"title": "API", "version": "1.0"}
        mock_parser.get_servers.return_value = [{"url": "https://default.com"}]
        mock_auth = Mock()
        mock_auth.auth_type = Mock(value="none")
        mock_parser.get_auth_config.return_value = mock_auth

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = []
        mock_agent.generate_from_openapi = Mock(return_value=mock_result)

        with patch("tool_factory.openapi.OpenAPIParser", return_value=mock_parser):
            with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
                with runner.isolated_filesystem():
                    with open("spec.json", "w") as f:
                        json.dump({"openapi": "3.0.0"}, f)

                    runner.invoke(
                        cli,
                        [
                            "from-openapi",
                            "spec.json",
                            "--base-url",
                            "https://custom.api.com",
                            "--output",
                            "./output",
                        ],
                    )

                    # Base URL passed to agent
                    call_args = mock_agent.generate_from_openapi.call_args
                    assert call_args[0][1] == "https://custom.api.com"


class TestTestCommandMocked:
    """Tests for test command with mocked subprocess."""

    def test_test_success(self, runner):
        """Test successful test run."""
        import subprocess
        from unittest.mock import Mock, patch

        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with runner.isolated_filesystem():
                os.makedirs("server/tests")
                with open("server/tests/test_example.py", "w") as f:
                    f.write("def test_example(): pass")

                runner.invoke(cli, ["test", "server"])

                mock_run.assert_called_once()
                assert "pytest" in str(mock_run.call_args)

    def test_test_failure(self, runner):
        """Test failed test run."""
        import subprocess
        from unittest.mock import Mock, patch

        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            with runner.isolated_filesystem():
                os.makedirs("server/tests")
                with open("server/tests/test_example.py", "w") as f:
                    f.write("def test_fail(): assert False")

                result = runner.invoke(cli, ["test", "server"])

                assert result.exit_code == 1


class TestServeCommandMocked:
    """Tests for serve command with mocked subprocess."""

    def test_serve_stdio(self, runner):
        """Test serve with stdio transport."""
        import subprocess
        from unittest.mock import Mock, patch

        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with runner.isolated_filesystem():
                os.makedirs("server")
                with open("server/server.py", "w") as f:
                    f.write("print('server')")

                runner.invoke(cli, ["serve", "server"])

                mock_run.assert_called_once()

    def test_serve_sse(self, runner):
        """Test serve with SSE transport."""
        import subprocess
        from unittest.mock import Mock, patch

        with patch.object(subprocess, "run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            with runner.isolated_filesystem():
                os.makedirs("server")
                with open("server/server.py", "w") as f:
                    f.write("print('server')")

                runner.invoke(
                    cli, ["serve", "server", "--transport", "sse", "--port", "9000"]
                )

                mock_run.assert_called_once()

    def test_serve_keyboard_interrupt(self, runner):
        """Test serve handles keyboard interrupt."""
        import subprocess
        from unittest.mock import patch

        with patch.object(subprocess, "run") as mock_run:
            mock_run.side_effect = KeyboardInterrupt()

            with runner.isolated_filesystem():
                os.makedirs("server")
                with open("server/server.py", "w") as f:
                    f.write("print('server')")

                result = runner.invoke(cli, ["serve", "server"])

                # Should handle gracefully
                assert "stopped" in result.output.lower() or result.exit_code == 0


class TestOutputPathHandling:
    """Tests for output path auto-directory creation."""

    def test_servers_subdirectory_created(self, runner):
        """Test that subdirectory is created under ./servers."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--name",
                        "MyTestServer",
                        "--output",
                        "./servers",
                    ],
                )

                # Verify write_to_directory was called with subdirectory
                call_args = mock_result.write_to_directory.call_args[0][0]
                assert "mytestserver" in call_args.lower()

    def test_custom_output_not_modified(self, runner):
        """Test that custom output path is used as-is."""
        from unittest.mock import Mock, patch

        mock_agent = Mock()
        mock_result = Mock()
        mock_result.tool_specs = [Mock(name="tool", description="Test")]
        mock_result.execution_log = None
        mock_agent.generate_from_description_sync.return_value = mock_result

        with patch("tool_factory.agent.ToolFactoryAgent", return_value=mock_agent):
            with runner.isolated_filesystem():
                runner.invoke(
                    cli,
                    [
                        "generate",
                        "Test tool",
                        "--name",
                        "TestServer",
                        "--output",
                        "./custom_output",
                    ],
                )

                # Verify write_to_directory was called with exact path
                call_args = mock_result.write_to_directory.call_args[0][0]
                assert "custom_output" in call_args
