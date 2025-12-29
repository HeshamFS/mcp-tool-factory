"""Dependency versioning utilities for generated MCP servers.

Provides realistic version constraints for common Python packages
used in MCP server implementations.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PackageVersion:
    """Version information for a package."""

    name: str
    min_version: str
    max_version: str | None = None
    extras: list[str] | None = None

    def to_requirement(self, style: str = "compatible") -> str:
        """Generate requirement string.

        Args:
            style: Versioning style
                - "compatible": Uses ~= for compatible release
                - "minimum": Uses >= for minimum version
                - "pinned": Uses == for exact version
                - "range": Uses >= and < for version range

        Returns:
            Requirement string like "package>=1.0.0,<2.0.0"
        """
        name_with_extras = self.name
        if self.extras:
            name_with_extras = f"{self.name}[{','.join(self.extras)}]"

        if style == "pinned":
            return f"{name_with_extras}=={self.min_version}"
        elif style == "compatible":
            return f"{name_with_extras}~={self.min_version}"
        elif style == "minimum":
            return f"{name_with_extras}>={self.min_version}"
        elif style == "range" and self.max_version:
            return f"{name_with_extras}>={self.min_version},<{self.max_version}"
        else:
            # Default to minimum with upper bound on major version
            major = self.min_version.split(".")[0]
            next_major = str(int(major) + 1)
            return f"{name_with_extras}>={self.min_version},<{next_major}.0.0"


# Known package versions for MCP servers
# Updated as of late 2024
KNOWN_PACKAGES: dict[str, PackageVersion] = {
    # Core MCP
    "mcp": PackageVersion("mcp", "1.0.0", "2.0.0"),
    "fastmcp": PackageVersion("fastmcp", "2.0.0", "3.0.0"),
    # HTTP/API
    "httpx": PackageVersion("httpx", "0.27.0", "1.0.0"),
    "aiohttp": PackageVersion("aiohttp", "3.9.0", "4.0.0"),
    "requests": PackageVersion("requests", "2.31.0", "3.0.0"),
    "urllib3": PackageVersion("urllib3", "2.0.0", "3.0.0"),
    # Async
    "anyio": PackageVersion("anyio", "4.0.0", "5.0.0"),
    "asyncio": PackageVersion("asyncio", "3.4.0"),
    # Data validation
    "pydantic": PackageVersion("pydantic", "2.5.0", "3.0.0"),
    "pydantic-settings": PackageVersion("pydantic-settings", "2.1.0", "3.0.0"),
    # Serialization
    "orjson": PackageVersion("orjson", "3.9.0", "4.0.0"),
    "ujson": PackageVersion("ujson", "5.9.0", "6.0.0"),
    # Database
    "sqlalchemy": PackageVersion("sqlalchemy", "2.0.0", "3.0.0"),
    "asyncpg": PackageVersion("asyncpg", "0.29.0", "1.0.0"),
    "aiosqlite": PackageVersion("aiosqlite", "0.19.0", "1.0.0"),
    "redis": PackageVersion("redis", "5.0.0", "6.0.0"),
    # Observability
    "opentelemetry-api": PackageVersion("opentelemetry-api", "1.22.0", "2.0.0"),
    "opentelemetry-sdk": PackageVersion("opentelemetry-sdk", "1.22.0", "2.0.0"),
    "opentelemetry-exporter-otlp": PackageVersion(
        "opentelemetry-exporter-otlp", "1.22.0", "2.0.0"
    ),
    "prometheus-client": PackageVersion("prometheus-client", "0.19.0", "1.0.0"),
    # Logging
    "structlog": PackageVersion("structlog", "24.1.0", "25.0.0"),
    "loguru": PackageVersion("loguru", "0.7.0", "1.0.0"),
    # CLI
    "click": PackageVersion("click", "8.1.0", "9.0.0"),
    "typer": PackageVersion("typer", "0.9.0", "1.0.0"),
    "rich": PackageVersion("rich", "13.7.0", "14.0.0"),
    # Testing
    "pytest": PackageVersion("pytest", "8.0.0", "9.0.0"),
    "pytest-asyncio": PackageVersion("pytest-asyncio", "0.23.0", "1.0.0"),
    "pytest-cov": PackageVersion("pytest-cov", "4.1.0", "5.0.0"),
    "httpx-mock": PackageVersion("httpx-mock", "0.30.0", "1.0.0"),
    # Security
    "cryptography": PackageVersion("cryptography", "41.0.0", "43.0.0"),
    "python-jose": PackageVersion("python-jose", "3.3.0", "4.0.0"),
    "passlib": PackageVersion("passlib", "1.7.4", "2.0.0"),
    # Utilities
    "python-dotenv": PackageVersion("python-dotenv", "1.0.0", "2.0.0"),
    "tenacity": PackageVersion("tenacity", "8.2.0", "9.0.0"),
    "cachetools": PackageVersion("cachetools", "5.3.0", "6.0.0"),
    # AI/ML clients
    "anthropic": PackageVersion("anthropic", "0.18.0", "1.0.0"),
    "openai": PackageVersion("openai", "1.12.0", "2.0.0"),
    "google-generativeai": PackageVersion("google-generativeai", "0.4.0", "1.0.0"),
    # File handling
    "pillow": PackageVersion("pillow", "10.2.0", "11.0.0"),
    "pypdf": PackageVersion("pypdf", "4.0.0", "5.0.0"),
    "openpyxl": PackageVersion("openpyxl", "3.1.0", "4.0.0"),
    # Web scraping
    "beautifulsoup4": PackageVersion("beautifulsoup4", "4.12.0", "5.0.0"),
    "lxml": PackageVersion("lxml", "5.1.0", "6.0.0"),
}


def get_package_version(
    package_name: str,
    style: str = "range",
) -> str:
    """Get version constraint for a known package.

    Args:
        package_name: Name of the package
        style: Versioning style (compatible, minimum, pinned, range)

    Returns:
        Requirement string
    """
    # Normalize package name
    normalized = package_name.lower().replace("_", "-")

    if normalized in KNOWN_PACKAGES:
        return KNOWN_PACKAGES[normalized].to_requirement(style)

    # Unknown package - use minimum version only
    return f"{package_name}>=0.1.0"


def generate_requirements(
    packages: list[str],
    style: str = "range",
    include_dev: bool = False,
) -> str:
    """Generate requirements.txt content.

    Args:
        packages: List of package names
        style: Versioning style
        include_dev: Whether to include development dependencies

    Returns:
        Requirements file content
    """
    lines = ["# Generated by MCP Tool Factory", ""]

    # Core dependencies
    lines.append("# Core dependencies")
    for pkg in packages:
        lines.append(get_package_version(pkg, style))

    if include_dev:
        lines.extend(
            [
                "",
                "# Development dependencies",
                get_package_version("pytest", style),
                get_package_version("pytest-asyncio", style),
                get_package_version("pytest-cov", style),
            ]
        )

    return "\n".join(lines)


def generate_pyproject_dependencies(
    packages: list[str],
    style: str = "range",
) -> dict[str, Any]:
    """Generate pyproject.toml dependencies section.

    Args:
        packages: List of package names
        style: Versioning style

    Returns:
        Dictionary suitable for pyproject.toml
    """
    dependencies = []

    for pkg in packages:
        dependencies.append(get_package_version(pkg, style))

    return {
        "dependencies": dependencies,
        "optional-dependencies": {
            "dev": [
                get_package_version("pytest", style),
                get_package_version("pytest-asyncio", style),
                get_package_version("pytest-cov", style),
            ],
            "redis": [
                get_package_version("redis", style),
            ],
            "telemetry": [
                get_package_version("opentelemetry-api", style),
                get_package_version("opentelemetry-sdk", style),
                get_package_version("opentelemetry-exporter-otlp", style),
            ],
        },
    }


def detect_packages_from_imports(code: str) -> list[str]:
    """Detect required packages from import statements.

    Args:
        code: Python source code

    Returns:
        List of detected package names
    """
    import re

    packages = set()

    # Match import statements
    import_pattern = r"^(?:from\s+(\w+)|import\s+(\w+))"

    for line in code.split("\n"):
        match = re.match(import_pattern, line.strip())
        if match:
            module = match.group(1) or match.group(2)
            if module:
                # Map common modules to package names
                package = MODULE_TO_PACKAGE.get(module, module)
                if package and package not in STDLIB_MODULES:
                    packages.add(package)

    return sorted(packages)


# Mapping of module names to package names
MODULE_TO_PACKAGE = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "jose": "python-jose",
}

# Standard library modules to exclude
STDLIB_MODULES = {
    "os",
    "sys",
    "re",
    "json",
    "math",
    "time",
    "datetime",
    "collections",
    "itertools",
    "functools",
    "typing",
    "dataclasses",
    "pathlib",
    "logging",
    "asyncio",
    "abc",
    "enum",
    "hashlib",
    "base64",
    "urllib",
    "uuid",
    "tempfile",
    "shutil",
    "io",
    "contextlib",
    "copy",
    "operator",
    "secrets",
    "random",
    "string",
    "textwrap",
    "threading",
    "multiprocessing",
}
