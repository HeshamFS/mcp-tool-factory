"""Data models for MCP Tool Factory."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class WebSearchEntry:
    """A single web search query and its results."""
    query: str
    results: str
    sources: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GenerationStep:
    """A single step in the generation process."""
    step_name: str
    description: str
    input_data: str | None = None
    output_data: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GenerationLog:
    """Complete log of the generation process."""
    # Metadata
    server_name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Configuration
    provider: str = ""
    model: str = ""
    web_search_enabled: bool = False

    # Input
    original_description: str = ""
    enhanced_description: str = ""

    # Web search results
    web_searches: list[WebSearchEntry] = field(default_factory=list)

    # Generation steps
    steps: list[GenerationStep] = field(default_factory=list)

    # Output summary
    tools_generated: list[str] = field(default_factory=list)
    dependencies_used: list[str] = field(default_factory=list)

    def add_step(self, name: str, description: str, input_data: str | None = None, output_data: str | None = None) -> None:
        """Add a generation step to the log."""
        self.steps.append(GenerationStep(
            step_name=name,
            description=description,
            input_data=input_data,
            output_data=output_data,
        ))

    def add_web_search(self, query: str, results: str, sources: list[str] | None = None) -> None:
        """Add a web search entry to the log."""
        self.web_searches.append(WebSearchEntry(
            query=query,
            results=results,
            sources=sources or [],
        ))

    def to_markdown(self) -> str:
        """Generate a markdown log file."""
        lines = [
            f"# Generation Log: {self.server_name}",
            "",
            f"**Created:** {self.created_at}",
            f"**Provider:** {self.provider}",
            f"**Model:** {self.model}",
            f"**Web Search:** {'Enabled' if self.web_search_enabled else 'Disabled'}",
            "",
            "---",
            "",
            "## Original Request",
            "",
            "```",
            self.original_description,
            "```",
            "",
        ]

        # Web search section
        if self.web_searches:
            lines.extend([
                "---",
                "",
                "## Web Research",
                "",
                "The following web searches were performed to gather context:",
                "",
            ])
            for i, search in enumerate(self.web_searches, 1):
                lines.extend([
                    f"### Search {i}: `{search.query}`",
                    "",
                    search.results[:2000] + ("..." if len(search.results) > 2000 else ""),
                    "",
                ])
                if search.sources:
                    lines.append("**Sources:**")
                    for source in search.sources[:5]:
                        lines.append(f"- {source}")
                    lines.append("")

        # Enhanced description
        if self.enhanced_description and self.enhanced_description != self.original_description:
            lines.extend([
                "---",
                "",
                "## Enhanced Description (with research)",
                "",
                "```",
                self.enhanced_description[:3000] + ("..." if len(self.enhanced_description) > 3000 else ""),
                "```",
                "",
            ])

        # Generation steps
        if self.steps:
            lines.extend([
                "---",
                "",
                "## Generation Steps",
                "",
            ])
            for i, step in enumerate(self.steps, 1):
                lines.extend([
                    f"### Step {i}: {step.step_name}",
                    "",
                    step.description,
                    "",
                ])
                if step.input_data:
                    lines.extend([
                        "<details>",
                        "<summary>Input Data</summary>",
                        "",
                        "```",
                        step.input_data[:1000] + ("..." if len(step.input_data) > 1000 else ""),
                        "```",
                        "</details>",
                        "",
                    ])
                if step.output_data:
                    lines.extend([
                        "<details>",
                        "<summary>Output Data</summary>",
                        "",
                        "```",
                        step.output_data[:1000] + ("..." if len(step.output_data) > 1000 else ""),
                        "```",
                        "</details>",
                        "",
                    ])

        # Tools generated
        if self.tools_generated:
            lines.extend([
                "---",
                "",
                "## Tools Generated",
                "",
            ])
            for tool in self.tools_generated:
                lines.append(f"- `{tool}`")
            lines.append("")

        # Dependencies
        if self.dependencies_used:
            lines.extend([
                "## Dependencies",
                "",
            ])
            for dep in self.dependencies_used:
                lines.append(f"- `{dep}`")
            lines.append("")

        return "\n".join(lines)


class InputType(Enum):
    """Types of inputs the factory can process."""

    NATURAL_LANGUAGE = "natural_language"
    OPENAPI = "openapi"
    PYTHON_FUNCTION = "python_function"
    DATABASE_SCHEMA = "database_schema"


@dataclass
class ToolSpec:
    """Specification for a tool to generate."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    implementation_hints: str | None = None
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "implementation_hints": self.implementation_hints,
            "dependencies": self.dependencies,
        }


@dataclass
class GeneratedServer:
    """Output from the tool factory."""

    name: str
    server_code: str
    tool_specs: list[ToolSpec]
    test_code: str
    dockerfile: str
    readme: str
    skill_file: str
    pyproject_toml: str
    github_actions: str = ""  # CI/CD workflow YAML
    execution_log: Any = None  # ExecutionLogger - imported dynamically to avoid circular imports

    def write_to_directory(self, output_path: str) -> None:
        """Write all generated files to a directory."""
        from pathlib import Path

        path = Path(output_path)
        path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (path / "tests").mkdir(exist_ok=True)

        # Write files
        (path / "server.py").write_text(self.server_code)
        (path / "tests" / "test_tools.py").write_text(self.test_code)
        (path / "tests" / "__init__.py").write_text("")
        (path / "Dockerfile").write_text(self.dockerfile)
        (path / "README.md").write_text(self.readme)
        (path / "skill.md").write_text(self.skill_file)
        (path / "pyproject.toml").write_text(self.pyproject_toml)

        # Write GitHub Actions workflow if available
        if self.github_actions:
            workflows_dir = path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            (workflows_dir / "ci.yml").write_text(self.github_actions)

        # Write execution log if available (real execution trace)
        if self.execution_log:
            (path / "EXECUTION_LOG.md").write_text(self.execution_log.to_markdown())
            (path / "execution_log.json").write_text(self.execution_log.to_json())


@dataclass
class ValidationResult:
    """Result of validating a tool specification."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
