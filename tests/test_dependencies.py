"""Tests for dependency versioning utilities."""

from tool_factory.utils.dependencies import (
    KNOWN_PACKAGES,
    PackageVersion,
    detect_packages_from_imports,
    generate_pyproject_dependencies,
    generate_requirements,
    get_package_version,
)


class TestPackageVersion:
    """Tests for PackageVersion dataclass."""

    def test_basic_version(self):
        """Test basic version creation."""
        pkg = PackageVersion("requests", "2.31.0", "3.0.0")
        assert pkg.name == "requests"
        assert pkg.min_version == "2.31.0"
        assert pkg.max_version == "3.0.0"

    def test_to_requirement_compatible(self):
        """Test compatible release versioning."""
        pkg = PackageVersion("requests", "2.31.0")
        req = pkg.to_requirement("compatible")
        assert req == "requests~=2.31.0"

    def test_to_requirement_minimum(self):
        """Test minimum version constraint."""
        pkg = PackageVersion("requests", "2.31.0")
        req = pkg.to_requirement("minimum")
        assert req == "requests>=2.31.0"

    def test_to_requirement_pinned(self):
        """Test pinned version."""
        pkg = PackageVersion("requests", "2.31.0")
        req = pkg.to_requirement("pinned")
        assert req == "requests==2.31.0"

    def test_to_requirement_range(self):
        """Test version range."""
        pkg = PackageVersion("requests", "2.31.0", "3.0.0")
        req = pkg.to_requirement("range")
        assert req == "requests>=2.31.0,<3.0.0"

    def test_to_requirement_with_extras(self):
        """Test requirement with extras."""
        pkg = PackageVersion("httpx", "0.27.0", extras=["http2"])
        req = pkg.to_requirement("minimum")
        assert req == "httpx[http2]>=0.27.0"

    def test_to_requirement_multiple_extras(self):
        """Test requirement with multiple extras."""
        pkg = PackageVersion("aiohttp", "3.9.0", extras=["speedups", "webserver"])
        req = pkg.to_requirement("minimum")
        assert "aiohttp[speedups,webserver]" in req

    def test_to_requirement_default_range(self):
        """Test default range based on major version."""
        pkg = PackageVersion("requests", "2.31.0")
        req = pkg.to_requirement("range")
        # Should use major version for upper bound
        assert ">=2.31.0" in req
        assert "<3.0.0" in req


class TestKnownPackages:
    """Tests for KNOWN_PACKAGES registry."""

    def test_has_core_packages(self):
        """Test core packages are defined."""
        assert "mcp" in KNOWN_PACKAGES
        assert "fastmcp" in KNOWN_PACKAGES
        assert "httpx" in KNOWN_PACKAGES
        assert "pydantic" in KNOWN_PACKAGES

    def test_has_database_packages(self):
        """Test database packages are defined."""
        assert "sqlalchemy" in KNOWN_PACKAGES
        assert "redis" in KNOWN_PACKAGES
        assert "asyncpg" in KNOWN_PACKAGES

    def test_has_observability_packages(self):
        """Test observability packages are defined."""
        assert "opentelemetry-api" in KNOWN_PACKAGES
        assert "prometheus-client" in KNOWN_PACKAGES

    def test_has_testing_packages(self):
        """Test testing packages are defined."""
        assert "pytest" in KNOWN_PACKAGES
        assert "pytest-asyncio" in KNOWN_PACKAGES

    def test_package_versions_are_realistic(self):
        """Test package versions are not placeholder values."""
        for name, pkg in KNOWN_PACKAGES.items():
            assert pkg.min_version != "0.0.0", f"{name} has placeholder version"
            assert pkg.min_version != "0.1.0", f"{name} might have generic version"
            # Min version should have at least major.minor
            parts = pkg.min_version.split(".")
            assert (
                len(parts) >= 2
            ), f"{name} version {pkg.min_version} should have major.minor"


class TestGetPackageVersion:
    """Tests for get_package_version function."""

    def test_known_package(self):
        """Test getting known package version."""
        req = get_package_version("requests")
        assert "requests" in req
        assert ">=" in req

    def test_known_package_with_style(self):
        """Test getting package with style."""
        req = get_package_version("pydantic", style="compatible")
        assert "~=" in req

    def test_unknown_package(self):
        """Test getting unknown package defaults to minimum."""
        req = get_package_version("some_unknown_package")
        assert "some_unknown_package>=0.1.0" == req

    def test_normalized_name(self):
        """Test package name normalization."""
        req1 = get_package_version("python-dotenv")
        get_package_version("python_dotenv")
        assert "python-dotenv" in req1
        # Both should work (normalization)


class TestGenerateRequirements:
    """Tests for generate_requirements function."""

    def test_basic_requirements(self):
        """Test basic requirements generation."""
        packages = ["mcp", "httpx", "pydantic"]
        content = generate_requirements(packages)

        assert "# Generated by MCP Tool Factory" in content
        assert "mcp" in content
        assert "httpx" in content
        assert "pydantic" in content

    def test_requirements_with_dev(self):
        """Test requirements with dev dependencies."""
        packages = ["mcp"]
        content = generate_requirements(packages, include_dev=True)

        assert "# Development dependencies" in content
        assert "pytest" in content
        assert "pytest-asyncio" in content

    def test_requirements_style(self):
        """Test requirements with different styles."""
        packages = ["httpx"]

        content_range = generate_requirements(packages, style="range")
        assert ">=" in content_range and "<" in content_range

        content_pinned = generate_requirements(packages, style="pinned")
        assert "==" in content_pinned


class TestGeneratePyprojectDependencies:
    """Tests for generate_pyproject_dependencies function."""

    def test_basic_dependencies(self):
        """Test basic pyproject dependencies."""
        packages = ["mcp", "httpx"]
        deps = generate_pyproject_dependencies(packages)

        assert "dependencies" in deps
        assert len(deps["dependencies"]) == 2

    def test_optional_dependencies(self):
        """Test optional dependency groups."""
        packages = ["mcp"]
        deps = generate_pyproject_dependencies(packages)

        assert "optional-dependencies" in deps
        assert "dev" in deps["optional-dependencies"]
        assert "redis" in deps["optional-dependencies"]
        assert "telemetry" in deps["optional-dependencies"]

    def test_dev_dependencies(self):
        """Test dev dependencies include testing packages."""
        packages = ["mcp"]
        deps = generate_pyproject_dependencies(packages)

        dev_deps = deps["optional-dependencies"]["dev"]
        assert any("pytest" in d for d in dev_deps)


class TestDetectPackagesFromImports:
    """Tests for detect_packages_from_imports function."""

    def test_detect_simple_import(self):
        """Test detecting simple imports."""
        code = """
import requests
import httpx
"""
        packages = detect_packages_from_imports(code)
        assert "requests" in packages
        assert "httpx" in packages

    def test_detect_from_import(self):
        """Test detecting from imports."""
        code = """
from pydantic import BaseModel
from httpx import AsyncClient
"""
        packages = detect_packages_from_imports(code)
        assert "pydantic" in packages
        assert "httpx" in packages

    def test_excludes_stdlib(self):
        """Test standard library is excluded."""
        code = """
import os
import sys
import json
from typing import Any
from dataclasses import dataclass
"""
        packages = detect_packages_from_imports(code)
        assert "os" not in packages
        assert "sys" not in packages
        assert "json" not in packages
        assert "typing" not in packages

    def test_maps_module_to_package(self):
        """Test module to package mapping."""
        code = """
from PIL import Image
import yaml
from bs4 import BeautifulSoup
"""
        packages = detect_packages_from_imports(code)
        assert "pillow" in packages
        assert "pyyaml" in packages
        assert "beautifulsoup4" in packages

    def test_returns_sorted(self):
        """Test packages are returned sorted."""
        code = """
import requests
import aiohttp
import httpx
"""
        packages = detect_packages_from_imports(code)
        assert packages == sorted(packages)

    def test_deduplicates(self):
        """Test duplicate imports are deduplicated."""
        code = """
import httpx
from httpx import AsyncClient
import httpx
"""
        packages = detect_packages_from_imports(code)
        assert packages.count("httpx") == 1
