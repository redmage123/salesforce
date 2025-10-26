#!/usr/bin/env python3
"""
Spring Boot Project Analyzer

Deep analysis of Spring Boot projects including:
- Application structure and layers
- REST endpoints mapping
- Database configuration
- Security setup
- Actuator endpoints
- Custom properties
- Bean definitions
- Async/Scheduled tasks
- Caching configuration
- Testing setup

Usage:
    from spring_boot_analyzer import SpringBootAnalyzer

    analyzer = SpringBootAnalyzer(project_dir="/path/to/spring-boot-app")
    analysis = analyzer.analyze()

    print(f"Main Application: {analysis.main_application_class}")
    print(f"REST Endpoints: {len(analysis.rest_endpoints)}")
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import re
import yaml
import logging


@dataclass
class RestEndpoint:
    """REST API endpoint"""
    path: str
    methods: List[str]  # GET, POST, PUT, DELETE, etc.
    controller_class: str
    method_name: str
    request_params: List[str] = field(default_factory=list)
    path_variables: List[str] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: Optional[str] = None
    driver_class: Optional[str] = None
    username: Optional[str] = None
    datasource_type: Optional[str] = None  # H2, PostgreSQL, MySQL, etc.


@dataclass
class SecurityConfig:
    """Security configuration"""
    enabled: bool = False
    oauth_enabled: bool = False
    jwt_enabled: bool = False
    basic_auth: bool = False
    form_login: bool = False
    cors_enabled: bool = False
    csrf_enabled: bool = True


@dataclass
class SpringBootAnalysis:
    """Comprehensive Spring Boot analysis"""
    # Application structure
    main_application_class: Optional[str] = None
    base_package: Optional[str] = None
    spring_boot_version: Optional[str] = None

    # Layers
    controllers: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    repositories: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    configurations: List[str] = field(default_factory=list)

    # REST API
    rest_endpoints: List[RestEndpoint] = field(default_factory=list)

    # Database
    database_config: Optional[DatabaseConfig] = None
    uses_jpa: bool = False
    uses_liquibase: bool = False
    uses_flyway: bool = False

    # Security
    security_config: Optional[SecurityConfig] = None

    # Spring Boot features
    actuator_enabled: bool = False
    actuator_endpoints: List[str] = field(default_factory=list)

    devtools_enabled: bool = False

    # Async/Scheduling
    has_async_methods: bool = False
    has_scheduled_tasks: bool = False

    # Caching
    caching_enabled: bool = False
    cache_provider: Optional[str] = None

    # Properties
    application_properties: Dict[str, str] = field(default_factory=dict)
    active_profiles: List[str] = field(default_factory=list)

    # Testing
    test_classes: List[str] = field(default_factory=list)
    uses_testcontainers: bool = False


class SpringBootAnalyzer:
    """
    Deep analyzer for Spring Boot applications.

    Scans source code, configuration files, and build files
    to provide comprehensive project analysis.
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Spring Boot analyzer.

        Args:
            project_dir: Spring Boot project root
            logger: Optional logger
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # Standard Spring Boot paths
        self.src_main = self.project_dir / "src" / "main" / "java"
        self.src_test = self.project_dir / "src" / "test" / "java"
        self.resources = self.project_dir / "src" / "main" / "resources"

    def analyze(self) -> SpringBootAnalysis:
        """
        Perform comprehensive Spring Boot analysis.

        Returns:
            SpringBootAnalysis with all detected information
        """
        analysis = SpringBootAnalysis()

        # Find main application class
        analysis.main_application_class = self._find_main_application_class()
        if analysis.main_application_class:
            analysis.base_package = self._extract_package(analysis.main_application_class)

        # Scan source code
        analysis.controllers = self._find_annotated_classes("@RestController", "@Controller")
        analysis.services = self._find_annotated_classes("@Service")
        analysis.repositories = self._find_annotated_classes("@Repository")
        analysis.entities = self._find_annotated_classes("@Entity")
        analysis.configurations = self._find_annotated_classes("@Configuration")

        # Analyze REST endpoints
        analysis.rest_endpoints = self._analyze_rest_endpoints()

        # Load and parse application properties
        analysis.application_properties = self._load_application_properties()
        analysis.active_profiles = self._get_active_profiles()

        # Database analysis
        analysis.database_config = self._analyze_database_config(analysis.application_properties)
        analysis.uses_jpa = self._check_jpa_usage()
        analysis.uses_liquibase = self._check_dependency("liquibase")
        analysis.uses_flyway = self._check_dependency("flyway")

        # Security analysis
        analysis.security_config = self._analyze_security()

        # Actuator
        analysis.actuator_enabled = self._check_dependency("spring-boot-starter-actuator")
        if analysis.actuator_enabled:
            analysis.actuator_endpoints = self._get_actuator_endpoints(analysis.application_properties)

        # DevTools
        analysis.devtools_enabled = self._check_dependency("spring-boot-devtools")

        # Async/Scheduling
        analysis.has_async_methods = self._check_annotation_usage("@Async")
        analysis.has_scheduled_tasks = self._check_annotation_usage("@Scheduled")

        # Caching
        analysis.caching_enabled = self._check_annotation_usage("@EnableCaching")
        analysis.cache_provider = self._detect_cache_provider()

        # Testing
        analysis.test_classes = self._find_test_classes()
        analysis.uses_testcontainers = self._check_dependency("testcontainers")

        # Spring Boot version
        analysis.spring_boot_version = self._get_spring_boot_version()

        return analysis

    def _find_main_application_class(self) -> Optional[str]:
        """Find the main Spring Boot application class"""
        if not self.src_main.exists():
            return None

        for java_file in self.src_main.glob("**/*.java"):
            content = java_file.read_text()

            if "@SpringBootApplication" in content:
                # Extract class name
                match = re.search(r'public\s+class\s+(\w+)', content)
                if match:
                    package = self._extract_package_from_file(java_file)
                    return f"{package}.{match.group(1)}"

        return None

    def _extract_package(self, fully_qualified_class: str) -> str:
        """Extract package from fully qualified class name"""
        parts = fully_qualified_class.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""

    def _extract_package_from_file(self, java_file: Path) -> str:
        """Extract package declaration from Java file"""
        content = java_file.read_text()
        match = re.search(r'package\s+([\w.]+);', content)
        return match.group(1) if match else ""

    def _find_annotated_classes(self, *annotations: str) -> List[str]:
        """Find classes with specific annotations"""
        classes = []

        if not self.src_main.exists():
            return classes

        for java_file in self.src_main.glob("**/*.java"):
            content = java_file.read_text()

            # Check if any annotation is present
            if any(ann in content for ann in annotations):
                # Extract class name
                match = re.search(r'public\s+(?:class|interface)\s+(\w+)', content)
                if match:
                    package = self._extract_package_from_file(java_file)
                    classes.append(f"{package}.{match.group(1)}")

        return classes

    def _analyze_rest_endpoints(self) -> List[RestEndpoint]:
        """Analyze REST API endpoints"""
        endpoints = []

        if not self.src_main.exists():
            return endpoints

        for java_file in self.src_main.glob("**/*.java"):
            content = java_file.read_text()

            if "@RestController" not in content and "@Controller" not in content:
                continue

            # Extract class name
            class_match = re.search(r'public\s+class\s+(\w+)', content)
            if not class_match:
                continue

            controller_class = class_match.group(1)

            # Extract base path from @RequestMapping on class
            class_path = ""
            class_mapping = re.search(r'@RequestMapping\(["\']([^"\']+)["\']\)', content)
            if class_mapping:
                class_path = class_mapping.group(1)

            # Find all endpoint methods
            # Match @GetMapping, @PostMapping, etc.
            method_patterns = [
                (r'@GetMapping\(["\']([^"\']+)["\']\)', ["GET"]),
                (r'@PostMapping\(["\']([^"\']+)["\']\)', ["POST"]),
                (r'@PutMapping\(["\']([^"\']+)["\']\)', ["PUT"]),
                (r'@DeleteMapping\(["\']([^"\']+)["\']\)', ["DELETE"]),
                (r'@PatchMapping\(["\']([^"\']+)["\']\)', ["PATCH"]),
                (r'@RequestMapping\([^)]*value\s*=\s*["\']([^"\']+)["\'][^)]*method\s*=\s*RequestMethod\.(\w+)', None),
            ]

            for pattern, methods in method_patterns:
                for match in re.finditer(pattern, content):
                    path = match.group(1)
                    full_path = f"{class_path}{path}".replace("//", "/")

                    # Extract method name
                    # Find the method definition after the annotation
                    method_start = match.end()
                    method_def = content[method_start:method_start+200]
                    method_name_match = re.search(r'public\s+\w+\s+(\w+)\s*\(', method_def)
                    method_name = method_name_match.group(1) if method_name_match else "unknown"

                    # Extract path variables
                    path_vars = re.findall(r'\{(\w+)\}', full_path)

                    if methods is None:
                        # Extract from RequestMethod.XXX
                        methods = [match.group(2)]

                    endpoints.append(RestEndpoint(
                        path=full_path,
                        methods=methods,
                        controller_class=controller_class,
                        method_name=method_name,
                        path_variables=path_vars
                    ))

        return endpoints

    def _load_application_properties(self) -> Dict[str, str]:
        """Load application.properties or application.yml"""
        properties = {}

        # Try application.properties
        props_file = self.resources / "application.properties"
        if props_file.exists():
            content = props_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    properties[key.strip()] = value.strip()

        # Try application.yml
        yml_file = self.resources / "application.yml"
        if yml_file.exists():
            try:
                with open(yml_file, 'r') as f:
                    yml_data = yaml.safe_load(f)
                    properties.update(self._flatten_yaml(yml_data))
            except Exception as e:
                self.logger.warning(f"Failed to parse application.yml: {e}")

        return properties

    def _flatten_yaml(self, data: dict, prefix: str = "") -> Dict[str, str]:
        """Flatten nested YAML structure to dot notation"""
        result = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self._flatten_yaml(value, full_key))
            else:
                result[full_key] = str(value)

        return result

    def _get_active_profiles(self) -> List[str]:
        """Get active Spring profiles"""
        profiles_prop = "spring.profiles.active"

        for props_file in [self.resources / "application.properties", self.resources / "application.yml"]:
            if props_file.exists():
                content = props_file.read_text()
                match = re.search(rf'{profiles_prop}[:\s=]+([^\n]+)', content)
                if match:
                    return [p.strip() for p in match.group(1).split(",")]

        return []

    def _analyze_database_config(self, properties: Dict[str, str]) -> DatabaseConfig:
        """Analyze database configuration"""
        config = DatabaseConfig()

        config.url = properties.get("spring.datasource.url")
        config.driver_class = properties.get("spring.datasource.driver-class-name")
        config.username = properties.get("spring.datasource.username")

        # Detect database type from URL
        if config.url:
            if "postgresql" in config.url.lower():
                config.datasource_type = "PostgreSQL"
            elif "mysql" in config.url.lower():
                config.datasource_type = "MySQL"
            elif "h2" in config.url.lower():
                config.datasource_type = "H2"
            elif "oracle" in config.url.lower():
                config.datasource_type = "Oracle"
            elif "sqlserver" in config.url.lower():
                config.datasource_type = "SQL Server"

        return config

    def _check_jpa_usage(self) -> bool:
        """Check if JPA is used"""
        return len(self._find_annotated_classes("@Entity")) > 0

    def _check_dependency(self, artifact_id: str) -> bool:
        """Check if dependency exists in build file"""
        pom = self.project_dir / "pom.xml"
        gradle = self.project_dir / "build.gradle"
        gradle_kts = self.project_dir / "build.gradle.kts"

        for build_file in [pom, gradle, gradle_kts]:
            if build_file.exists():
                content = build_file.read_text()
                if artifact_id in content:
                    return True

        return False

    def _analyze_security(self) -> SecurityConfig:
        """Analyze security configuration"""
        config = SecurityConfig()

        config.enabled = self._check_dependency("spring-boot-starter-security")
        config.oauth_enabled = self._check_dependency("spring-security-oauth2")
        config.jwt_enabled = self._check_dependency("jjwt")

        # Check for security configurations
        for java_file in self.src_main.glob("**/*Security*.java"):
            content = java_file.read_text()

            if "httpBasic()" in content:
                config.basic_auth = True
            if "formLogin()" in content:
                config.form_login = True
            if ".cors()" in content:
                config.cors_enabled = True
            if "csrf().disable()" in content:
                config.csrf_enabled = False

        return config

    def _get_actuator_endpoints(self, properties: Dict[str, str]) -> List[str]:
        """Get enabled actuator endpoints"""
        endpoints = []

        # Check if all endpoints are exposed
        expose_prop = properties.get("management.endpoints.web.exposure.include", "")

        if expose_prop == "*":
            # All endpoints exposed
            endpoints = ["health", "info", "metrics", "env", "beans", "mappings", "loggers"]
        elif expose_prop:
            endpoints = [e.strip() for e in expose_prop.split(",")]
        else:
            # Default endpoints
            endpoints = ["health", "info"]

        return endpoints

    def _check_annotation_usage(self, annotation: str) -> bool:
        """Check if annotation is used in source code"""
        if not self.src_main.exists():
            return False

        for java_file in self.src_main.glob("**/*.java"):
            content = java_file.read_text()
            if annotation in content:
                return True

        return False

    def _detect_cache_provider(self) -> Optional[str]:
        """Detect caching provider"""
        if self._check_dependency("spring-boot-starter-cache"):
            if self._check_dependency("caffeine"):
                return "Caffeine"
            elif self._check_dependency("ehcache"):
                return "EhCache"
            elif self._check_dependency("hazelcast"):
                return "Hazelcast"
            elif self._check_dependency("redis"):
                return "Redis"
            return "Simple (in-memory)"

        return None

    def _find_test_classes(self) -> List[str]:
        """Find test classes"""
        test_classes = []

        if not self.src_test.exists():
            return test_classes

        for java_file in self.src_test.glob("**/*Test.java"):
            package = self._extract_package_from_file(java_file)
            class_name = java_file.stem
            test_classes.append(f"{package}.{class_name}")

        return test_classes

    def _get_spring_boot_version(self) -> Optional[str]:
        """Get Spring Boot version from build file"""
        pom = self.project_dir / "pom.xml"

        if pom.exists():
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(pom)
                root = tree.getroot()
                ns = {"mvn": "http://maven.apache.org/POM/4.0.0"}

                # Check parent
                parent = root.find(".//mvn:parent", ns)
                if parent is not None:
                    artifact = parent.find("mvn:artifactId", ns)
                    if artifact is not None and "spring-boot" in artifact.text:
                        version = parent.find("mvn:version", ns)
                        if version is not None:
                            return version.text

                # Check dependencies
                for dep in root.findall(".//mvn:dependency", ns):
                    artifact = dep.find("mvn:artifactId", ns)
                    if artifact is not None and "spring-boot-starter" in artifact.text:
                        version = dep.find("mvn:version", ns)
                        if version is not None:
                            return version.text

            except Exception as e:
                self.logger.warning(f"Failed to parse pom.xml: {e}")

        return None


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Spring Boot Project Analyzer"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Spring Boot project directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create analyzer
    analyzer = SpringBootAnalyzer(project_dir=args.project_dir)

    # Analyze project
    analysis = analyzer.analyze()

    # Output results
    if args.json:
        result = {
            "main_class": analysis.main_application_class,
            "base_package": analysis.base_package,
            "spring_boot_version": analysis.spring_boot_version,
            "controllers": len(analysis.controllers),
            "services": len(analysis.services),
            "repositories": len(analysis.repositories),
            "entities": len(analysis.entities),
            "rest_endpoints": len(analysis.rest_endpoints),
            "database": analysis.database_config.datasource_type if analysis.database_config else None,
            "security_enabled": analysis.security_config.enabled if analysis.security_config else False,
            "actuator_enabled": analysis.actuator_enabled,
            "test_classes": len(analysis.test_classes)
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Spring Boot Application Analysis")
        print(f"{'='*60}")
        print(f"Main Class:    {analysis.main_application_class}")
        print(f"Base Package:  {analysis.base_package}")
        if analysis.spring_boot_version:
            print(f"Spring Boot:   {analysis.spring_boot_version}")

        print(f"\nLayers:")
        print(f"  Controllers:  {len(analysis.controllers)}")
        print(f"  Services:     {len(analysis.services)}")
        print(f"  Repositories: {len(analysis.repositories)}")
        print(f"  Entities:     {len(analysis.entities)}")

        print(f"\nREST API:")
        print(f"  Endpoints:    {len(analysis.rest_endpoints)}")
        for endpoint in analysis.rest_endpoints[:5]:  # Show first 5
            print(f"    {', '.join(endpoint.methods):6} {endpoint.path}")

        if analysis.database_config and analysis.database_config.datasource_type:
            print(f"\nDatabase:")
            print(f"  Type:         {analysis.database_config.datasource_type}")
            print(f"  JPA:          {'Yes' if analysis.uses_jpa else 'No'}")

        if analysis.security_config and analysis.security_config.enabled:
            print(f"\nSecurity:")
            print(f"  OAuth:        {'Yes' if analysis.security_config.oauth_enabled else 'No'}")
            print(f"  JWT:          {'Yes' if analysis.security_config.jwt_enabled else 'No'}")

        if analysis.actuator_enabled:
            print(f"\nActuator:")
            print(f"  Endpoints:    {', '.join(analysis.actuator_endpoints)}")

        print(f"\nTesting:")
        print(f"  Test Classes: {len(analysis.test_classes)}")
        print(f"  Testcontainers: {'Yes' if analysis.uses_testcontainers else 'No'}")

        print(f"{'='*60}\n")
