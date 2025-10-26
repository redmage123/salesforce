#!/usr/bin/env python3
"""
Universal Build System for Artemis

Automatically detects, selects, and creates appropriate build configurations
for ANY project across all major programming languages and ecosystems.

Supported Build Systems:
- Java: Maven, Gradle, Ant
- JavaScript/Node.js: npm, yarn, pnpm
- Python: pip, poetry, pipenv
- C/C++: CMake, Make
- Rust: Cargo
- Go: go mod
- .NET: dotnet/NuGet
- Ruby: Bundler
- PHP: Composer

Usage:
    from universal_build_system import UniversalBuildSystem

    ubs = UniversalBuildSystem(project_dir="/path/to/project")

    # Auto-detect build system
    build_system = ubs.detect_build_system()

    # Or let Artemis decide for new project
    recommended = ubs.recommend_build_system(
        language="python",
        project_type="web_api"
    )

    # Create build configuration
    ubs.create_build_config(build_system="poetry", language="python")

    # Build project
    result = ubs.build()

    # Run tests
    test_result = ubs.test()
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import json


class BuildSystem(Enum):
    """All supported build systems"""
    # Java
    MAVEN = "maven"
    GRADLE = "gradle"
    ANT = "ant"

    # JavaScript/Node.js
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"

    # Python
    PIP = "pip"
    POETRY = "poetry"
    PIPENV = "pipenv"
    CONDA = "conda"

    # C/C++
    CMAKE = "cmake"
    MAKE = "make"

    # Rust
    CARGO = "cargo"

    # Go
    GO_MOD = "go"

    # .NET
    DOTNET = "dotnet"
    NUGET = "nuget"

    # Ruby
    BUNDLER = "bundler"

    # PHP
    COMPOSER = "composer"

    # Unknown
    UNKNOWN = "unknown"


class Language(Enum):
    """Programming languages"""
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    CPP = "cpp"
    C = "c"
    RUST = "rust"
    GO = "go"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


class ProjectType(Enum):
    """Project types"""
    WEB_API = "web_api"
    WEB_FRONTEND = "web_frontend"
    WEB_FULLSTACK = "web_fullstack"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    MICROSERVICE = "microservice"
    DESKTOP_APP = "desktop_app"
    MOBILE_APP = "mobile_app"
    DATA_SCIENCE = "data_science"
    UNKNOWN = "unknown"


@dataclass
class BuildSystemDetection:
    """Build system detection result"""
    build_system: BuildSystem
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    language: Language = Language.UNKNOWN
    project_type: ProjectType = ProjectType.UNKNOWN


@dataclass
class BuildSystemRecommendation:
    """Build system recommendation"""
    build_system: BuildSystem
    rationale: str
    alternatives: List[BuildSystem] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class BuildResult:
    """Universal build result"""
    success: bool
    exit_code: int
    duration: float
    output: str
    build_system: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class UniversalBuildSystem:
    """
    Universal build system manager for Artemis.

    Automatically detects or recommends the appropriate build system
    for any project and provides unified build/test interface.
    """

    # Build system file indicators
    BUILD_INDICATORS = {
        BuildSystem.MAVEN: ["pom.xml"],
        BuildSystem.GRADLE: ["build.gradle", "build.gradle.kts", "settings.gradle"],
        BuildSystem.ANT: ["build.xml"],
        BuildSystem.NPM: ["package.json", "package-lock.json"],
        BuildSystem.YARN: ["yarn.lock"],
        BuildSystem.PNPM: ["pnpm-lock.yaml"],
        BuildSystem.PIP: ["requirements.txt", "setup.py"],
        BuildSystem.POETRY: ["pyproject.toml", "poetry.lock"],
        BuildSystem.PIPENV: ["Pipfile", "Pipfile.lock"],
        BuildSystem.CONDA: ["environment.yml", "conda.yml"],
        BuildSystem.CMAKE: ["CMakeLists.txt"],
        BuildSystem.MAKE: ["Makefile"],
        BuildSystem.CARGO: ["Cargo.toml", "Cargo.lock"],
        BuildSystem.GO_MOD: ["go.mod", "go.sum"],
        BuildSystem.DOTNET: ["*.csproj", "*.sln"],
        BuildSystem.BUNDLER: ["Gemfile", "Gemfile.lock"],
        BuildSystem.COMPOSER: ["composer.json", "composer.lock"],
    }

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        Language.JAVA: ["**/*.java"],
        Language.JAVASCRIPT: ["**/*.js", "**/*.jsx"],
        Language.TYPESCRIPT: ["**/*.ts", "**/*.tsx"],
        Language.PYTHON: ["**/*.py"],
        Language.CPP: ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp"],
        Language.C: ["**/*.c", "**/*.h"],
        Language.RUST: ["**/*.rs"],
        Language.GO: ["**/*.go"],
        Language.CSHARP: ["**/*.cs"],
        Language.RUBY: ["**/*.rb"],
        Language.PHP: ["**/*.php"],
    }

    # Recommended build systems by language and project type
    RECOMMENDATIONS = {
        (Language.JAVA, ProjectType.WEB_API): BuildSystem.MAVEN,
        (Language.JAVA, ProjectType.MICROSERVICE): BuildSystem.GRADLE,
        (Language.JAVA, ProjectType.LIBRARY): BuildSystem.GRADLE,
        (Language.JAVASCRIPT, ProjectType.WEB_FRONTEND): BuildSystem.NPM,
        (Language.JAVASCRIPT, ProjectType.WEB_API): BuildSystem.NPM,
        (Language.TYPESCRIPT, ProjectType.WEB_FRONTEND): BuildSystem.NPM,
        (Language.TYPESCRIPT, ProjectType.WEB_API): BuildSystem.NPM,
        (Language.PYTHON, ProjectType.WEB_API): BuildSystem.POETRY,
        (Language.PYTHON, ProjectType.CLI_TOOL): BuildSystem.POETRY,
        (Language.PYTHON, ProjectType.LIBRARY): BuildSystem.POETRY,
        (Language.PYTHON, ProjectType.DATA_SCIENCE): BuildSystem.CONDA,
        (Language.CPP, ProjectType.LIBRARY): BuildSystem.CMAKE,
        (Language.CPP, ProjectType.CLI_TOOL): BuildSystem.CMAKE,
        (Language.RUST, ProjectType.CLI_TOOL): BuildSystem.CARGO,
        (Language.RUST, ProjectType.LIBRARY): BuildSystem.CARGO,
        (Language.GO, ProjectType.WEB_API): BuildSystem.GO_MOD,
        (Language.GO, ProjectType.MICROSERVICE): BuildSystem.GO_MOD,
        (Language.CSHARP, ProjectType.WEB_API): BuildSystem.DOTNET,
        (Language.RUBY, ProjectType.WEB_API): BuildSystem.BUNDLER,
        (Language.PHP, ProjectType.WEB_API): BuildSystem.COMPOSER,
    }

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize universal build system.

        Args:
            project_dir: Project root directory
            logger: Optional logger
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

    def detect_build_system(self) -> BuildSystemDetection:
        """
        Automatically detect build system from project files.

        Returns:
            BuildSystemDetection with detected build system
        """
        detections = []

        # Check for build system indicators
        for build_system, indicators in self.BUILD_INDICATORS.items():
            evidence = []

            for indicator in indicators:
                # Handle glob patterns
                if "*" in indicator:
                    matches = list(self.project_dir.glob(indicator))
                    if matches:
                        evidence.extend([str(m.relative_to(self.project_dir)) for m in matches])
                else:
                    file_path = self.project_dir / indicator
                    if file_path.exists():
                        evidence.append(indicator)

            if evidence:
                # Calculate confidence based on evidence strength
                confidence = min(1.0, len(evidence) * 0.3 + 0.4)

                detections.append(BuildSystemDetection(
                    build_system=build_system,
                    confidence=confidence,
                    evidence=evidence
                ))

        if not detections:
            return BuildSystemDetection(
                build_system=BuildSystem.UNKNOWN,
                confidence=0.0,
                evidence=[]
            )

        # Return highest confidence detection
        best_detection = max(detections, key=lambda d: d.confidence)

        # Detect language
        best_detection.language = self._detect_language()

        # Detect project type
        best_detection.project_type = self._detect_project_type()

        return best_detection

    def recommend_build_system(
        self,
        language: str,
        project_type: str = "unknown"
    ) -> BuildSystemRecommendation:
        """
        Recommend build system for new project.

        Args:
            language: Programming language
            project_type: Type of project

        Returns:
            BuildSystemRecommendation with recommended system
        """
        lang_enum = Language(language.lower()) if language else Language.UNKNOWN
        type_enum = ProjectType(project_type.lower()) if project_type else ProjectType.UNKNOWN

        # Get recommendation from lookup table
        build_system = self.RECOMMENDATIONS.get(
            (lang_enum, type_enum),
            self._get_default_for_language(lang_enum)
        )

        rationale = self._get_rationale(build_system, lang_enum, type_enum)
        alternatives = self._get_alternatives(build_system, lang_enum)

        return BuildSystemRecommendation(
            build_system=build_system,
            rationale=rationale,
            alternatives=alternatives,
            confidence=0.9
        )

    def _detect_language(self) -> Language:
        """Detect primary programming language"""
        language_counts = {}

        for language, patterns in self.LANGUAGE_PATTERNS.items():
            count = 0
            for pattern in patterns:
                count += len(list(self.project_dir.glob(pattern)))

            if count > 0:
                language_counts[language] = count

        if not language_counts:
            return Language.UNKNOWN

        # Return language with most files
        return max(language_counts.items(), key=lambda x: x[1])[0]

    def _detect_project_type(self) -> ProjectType:
        """Detect project type from structure and files"""
        # Check for web indicators
        has_web = any([
            (self.project_dir / "public").exists(),
            (self.project_dir / "static").exists(),
            (self.project_dir / "templates").exists(),
            list(self.project_dir.glob("**/*Controller.java")),
            list(self.project_dir.glob("**/routes.py")),
        ])

        # Check for API indicators
        has_api = any([
            list(self.project_dir.glob("**/api/**")),
            list(self.project_dir.glob("**/endpoints/**")),
        ])

        # Check for CLI indicators
        has_cli = any([
            (self.project_dir / "bin").exists(),
            (self.project_dir / "cli.py").exists(),
            (self.project_dir / "main.rs").exists(),
        ])

        if has_web and has_api:
            return ProjectType.WEB_FULLSTACK
        elif has_api:
            return ProjectType.WEB_API
        elif has_web:
            return ProjectType.WEB_FRONTEND
        elif has_cli:
            return ProjectType.CLI_TOOL
        else:
            return ProjectType.LIBRARY

    def _get_default_for_language(self, language: Language) -> BuildSystem:
        """Get default build system for language"""
        defaults = {
            Language.JAVA: BuildSystem.MAVEN,
            Language.JAVASCRIPT: BuildSystem.NPM,
            Language.TYPESCRIPT: BuildSystem.NPM,
            Language.PYTHON: BuildSystem.POETRY,
            Language.CPP: BuildSystem.CMAKE,
            Language.C: BuildSystem.CMAKE,
            Language.RUST: BuildSystem.CARGO,
            Language.GO: BuildSystem.GO_MOD,
            Language.CSHARP: BuildSystem.DOTNET,
            Language.RUBY: BuildSystem.BUNDLER,
            Language.PHP: BuildSystem.COMPOSER,
        }
        return defaults.get(language, BuildSystem.UNKNOWN)

    def _get_rationale(
        self,
        build_system: BuildSystem,
        language: Language,
        project_type: ProjectType
    ) -> str:
        """Get rationale for build system choice"""
        rationales = {
            BuildSystem.MAVEN: "Maven is the industry standard for Java projects with convention-over-configuration",
            BuildSystem.GRADLE: "Gradle provides flexible build scripting for complex Java projects",
            BuildSystem.NPM: "npm is the default package manager for Node.js/JavaScript ecosystem",
            BuildSystem.POETRY: "Poetry provides modern dependency management and packaging for Python",
            BuildSystem.CMAKE: "CMake is the cross-platform build system standard for C/C++",
            BuildSystem.CARGO: "Cargo is the official Rust package manager and build tool",
            BuildSystem.GO_MOD: "Go modules is the standard dependency management for Go",
            BuildSystem.DOTNET: "dotnet CLI is the official build tool for .NET projects",
            BuildSystem.BUNDLER: "Bundler is the standard gem dependency manager for Ruby",
            BuildSystem.COMPOSER: "Composer is the standard dependency manager for PHP",
        }

        return rationales.get(
            build_system,
            f"{build_system.value} is recommended for {language.value} {project_type.value} projects"
        )

    def _get_alternatives(
        self,
        build_system: BuildSystem,
        language: Language
    ) -> List[BuildSystem]:
        """Get alternative build systems"""
        alternatives_map = {
            (BuildSystem.MAVEN, Language.JAVA): [BuildSystem.GRADLE],
            (BuildSystem.GRADLE, Language.JAVA): [BuildSystem.MAVEN],
            (BuildSystem.NPM, Language.JAVASCRIPT): [BuildSystem.YARN, BuildSystem.PNPM],
            (BuildSystem.POETRY, Language.PYTHON): [BuildSystem.PIP, BuildSystem.PIPENV],
        }

        return alternatives_map.get((build_system, language), [])

    def get_build_manager(self, build_system: BuildSystem = None):
        """
        Get appropriate build manager instance.

        Args:
            build_system: Specific build system (auto-detected if None)

        Returns:
            Build manager instance
        """
        if build_system is None:
            detection = self.detect_build_system()
            build_system = detection.build_system

        # Import and return appropriate manager
        if build_system == BuildSystem.MAVEN:
            from maven_manager import MavenManager
            return MavenManager(self.project_dir, self.logger)

        elif build_system == BuildSystem.GRADLE:
            from gradle_manager import GradleManager
            return GradleManager(self.project_dir, self.logger)

        # Other build systems will be implemented
        else:
            raise NotImplementedError(
                f"Build system {build_system.value} not yet implemented"
            )


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Universal Build System for Artemis"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect build system")
    detect_parser.add_argument("--json", action="store_true", help="JSON output")

    # Recommend command
    recommend_parser = subparsers.add_parser("recommend", help="Recommend build system")
    recommend_parser.add_argument("--language", required=True, help="Programming language")
    recommend_parser.add_argument("--type", help="Project type")
    recommend_parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create universal build system
    ubs = UniversalBuildSystem(project_dir=args.project_dir)

    if args.command == "detect":
        detection = ubs.detect_build_system()

        if args.json:
            result = {
                "build_system": detection.build_system.value,
                "confidence": detection.confidence,
                "evidence": detection.evidence,
                "language": detection.language.value,
                "project_type": detection.project_type.value
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Build System Detection")
            print(f"{'='*60}")
            print(f"Build System:  {detection.build_system.value}")
            print(f"Confidence:    {detection.confidence * 100:.0f}%")
            print(f"Language:      {detection.language.value}")
            print(f"Project Type:  {detection.project_type.value}")
            if detection.evidence:
                print(f"Evidence:")
                for evidence in detection.evidence:
                    print(f"  - {evidence}")
            print(f"{'='*60}\n")

    elif args.command == "recommend":
        recommendation = ubs.recommend_build_system(
            language=args.language,
            project_type=args.type or "unknown"
        )

        if args.json:
            result = {
                "build_system": recommendation.build_system.value,
                "rationale": recommendation.rationale,
                "alternatives": [alt.value for alt in recommendation.alternatives],
                "confidence": recommendation.confidence
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Build System Recommendation")
            print(f"{'='*60}")
            print(f"Recommended:  {recommendation.build_system.value}")
            print(f"Rationale:    {recommendation.rationale}")
            print(f"Confidence:   {recommendation.confidence * 100:.0f}%")
            if recommendation.alternatives:
                alts = ", ".join([alt.value for alt in recommendation.alternatives])
                print(f"Alternatives: {alts}")
            print(f"{'='*60}\n")

    else:
        parser.print_help()
