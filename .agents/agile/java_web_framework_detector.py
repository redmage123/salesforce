#!/usr/bin/env python3
"""
Java Web Framework Detector and Analyzer

Detects and analyzes Java web frameworks and technologies:
- Spring Boot / Spring Framework
- Jakarta EE (formerly Java EE)
- Micronaut
- Quarkus
- Play Framework
- Dropwizard
- Vert.x
- Spark Framework
- Struts
- JSF (JavaServer Faces)

Provides comprehensive analysis of:
- Framework version
- Web server (Tomcat, Jetty, Undertow, etc.)
- Database connectivity
- Template engines
- REST/GraphQL APIs
- Security frameworks
- Testing frameworks

Usage:
    from java_web_framework_detector import JavaWebFrameworkDetector

    detector = JavaWebFrameworkDetector(project_dir="/path/to/project")
    analysis = detector.analyze()

    print(f"Framework: {analysis.primary_framework}")
    print(f"Version: {analysis.framework_version}")
    print(f"Web Server: {analysis.web_server}")
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import xml.etree.ElementTree as ET
import re
import logging


class JavaWebFramework(Enum):
    """Java web frameworks"""
    SPRING_BOOT = "Spring Boot"
    SPRING_MVC = "Spring MVC"
    JAKARTA_EE = "Jakarta EE"
    MICRONAUT = "Micronaut"
    QUARKUS = "Quarkus"
    PLAY = "Play Framework"
    DROPWIZARD = "Dropwizard"
    VERTX = "Vert.x"
    SPARK = "Spark Framework"
    STRUTS = "Apache Struts"
    JSF = "JavaServer Faces"
    VAADIN = "Vaadin"
    GRAILS = "Grails"
    UNKNOWN = "Unknown"


class WebServer(Enum):
    """Java web servers / servlet containers"""
    TOMCAT = "Apache Tomcat"
    JETTY = "Eclipse Jetty"
    UNDERTOW = "Undertow"
    NETTY = "Netty"
    GLASSFISH = "GlassFish"
    WILDFLY = "WildFly"
    WEBLOGIC = "WebLogic"
    WEBSPHERE = "WebSphere"
    JBOSS = "JBoss"
    UNKNOWN = "Unknown"


class TemplateEngine(Enum):
    """Java template engines"""
    THYMELEAF = "Thymeleaf"
    FREEMARKER = "FreeMarker"
    VELOCITY = "Velocity"
    JSP = "JavaServer Pages"
    MUSTACHE = "Mustache"
    PEBBLE = "Pebble"
    GROOVY = "Groovy Templates"
    UNKNOWN = "Unknown"


@dataclass
class JavaWebFrameworkAnalysis:
    """Comprehensive Java web framework analysis"""
    primary_framework: JavaWebFramework
    framework_version: Optional[str] = None
    web_server: WebServer = WebServer.UNKNOWN
    web_server_version: Optional[str] = None

    # Build system
    build_system: str = "Unknown"  # Maven, Gradle

    # Template engines
    template_engines: List[TemplateEngine] = field(default_factory=list)

    # Database
    database_technologies: List[str] = field(default_factory=list)  # JPA, Hibernate, MyBatis, JDBC
    databases: List[str] = field(default_factory=list)  # PostgreSQL, MySQL, H2, etc.

    # APIs
    has_rest_api: bool = False
    has_graphql: bool = False
    has_soap: bool = False
    rest_framework: Optional[str] = None  # JAX-RS, Spring Web

    # Security
    security_frameworks: List[str] = field(default_factory=list)  # Spring Security, Shiro, etc.
    has_oauth: bool = False
    has_jwt: bool = False

    # Testing
    test_frameworks: List[str] = field(default_factory=list)  # JUnit, TestNG, Mockito, etc.

    # Additional technologies
    messaging: List[str] = field(default_factory=list)  # JMS, Kafka, RabbitMQ
    caching: List[str] = field(default_factory=list)  # Redis, Hazelcast, EhCache

    # Configuration
    config_format: str = "Unknown"  # application.properties, application.yml, etc.

    # Detected dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)

    # Source structure
    is_microservices: bool = False
    is_monolith: bool = True
    modules: List[str] = field(default_factory=list)


class JavaWebFrameworkDetector:
    """
    Intelligent Java web framework detector and analyzer.

    Analyzes Maven/Gradle projects to detect web frameworks,
    web servers, databases, and other technologies.
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize detector.

        Args:
            project_dir: Java project root directory
            logger: Optional logger
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # Locate build files
        self.pom_path = self.project_dir / "pom.xml"
        self.gradle_path = self.project_dir / "build.gradle"
        self.gradle_kts_path = self.project_dir / "build.gradle.kts"

    def analyze(self) -> JavaWebFrameworkAnalysis:
        """
        Perform comprehensive Java web framework analysis.

        Returns:
            JavaWebFrameworkAnalysis with detected technologies
        """
        # Detect build system
        build_system = self._detect_build_system()

        # Parse dependencies
        dependencies = self._parse_dependencies(build_system)

        # Detect primary framework
        framework = self._detect_framework(dependencies)
        framework_version = self._get_framework_version(framework, dependencies)

        # Detect web server
        web_server = self._detect_web_server(dependencies)
        web_server_version = self._get_web_server_version(web_server, dependencies)

        # Detect template engines
        template_engines = self._detect_template_engines(dependencies)

        # Detect database technologies
        db_techs = self._detect_database_technologies(dependencies)
        databases = self._detect_databases(dependencies)

        # Detect API technologies
        has_rest, rest_framework = self._detect_rest_api(dependencies)
        has_graphql = self._detect_graphql(dependencies)
        has_soap = self._detect_soap(dependencies)

        # Detect security
        security_frameworks = self._detect_security_frameworks(dependencies)
        has_oauth = self._detect_oauth(dependencies)
        has_jwt = self._detect_jwt(dependencies)

        # Detect testing frameworks
        test_frameworks = self._detect_test_frameworks(dependencies)

        # Detect messaging
        messaging = self._detect_messaging(dependencies)

        # Detect caching
        caching = self._detect_caching(dependencies)

        # Detect configuration format
        config_format = self._detect_config_format()

        # Detect architecture
        is_microservices, is_monolith, modules = self._detect_architecture()

        return JavaWebFrameworkAnalysis(
            primary_framework=framework,
            framework_version=framework_version,
            web_server=web_server,
            web_server_version=web_server_version,
            build_system=build_system,
            template_engines=template_engines,
            database_technologies=db_techs,
            databases=databases,
            has_rest_api=has_rest,
            has_graphql=has_graphql,
            has_soap=has_soap,
            rest_framework=rest_framework,
            security_frameworks=security_frameworks,
            has_oauth=has_oauth,
            has_jwt=has_jwt,
            test_frameworks=test_frameworks,
            messaging=messaging,
            caching=caching,
            config_format=config_format,
            dependencies=dependencies,
            is_microservices=is_microservices,
            is_monolith=is_monolith,
            modules=modules
        )

    def _detect_build_system(self) -> str:
        """Detect build system (Maven or Gradle)"""
        if self.pom_path.exists():
            return "Maven"
        elif self.gradle_path.exists() or self.gradle_kts_path.exists():
            return "Gradle"
        return "Unknown"

    def _parse_dependencies(self, build_system: str) -> Dict[str, str]:
        """Parse dependencies from build file"""
        if build_system == "Maven":
            return self._parse_maven_dependencies()
        elif build_system == "Gradle":
            return self._parse_gradle_dependencies()
        return {}

    def _parse_maven_dependencies(self) -> Dict[str, str]:
        """Parse dependencies from pom.xml"""
        if not self.pom_path.exists():
            return {}

        try:
            tree = ET.parse(self.pom_path)
            root = tree.getroot()

            # Handle Maven namespace
            ns = {"mvn": "http://maven.apache.org/POM/4.0.0"}

            dependencies = {}

            for dep in root.findall(".//mvn:dependency", ns):
                group_id = dep.find("mvn:groupId", ns)
                artifact_id = dep.find("mvn:artifactId", ns)
                version = dep.find("mvn:version", ns)

                if group_id is not None and artifact_id is not None:
                    key = f"{group_id.text}:{artifact_id.text}"
                    dependencies[key] = version.text if version is not None else "unknown"

            return dependencies

        except Exception as e:
            self.logger.error(f"Failed to parse Maven dependencies: {e}")
            return {}

    def _parse_gradle_dependencies(self) -> Dict[str, str]:
        """Parse dependencies from build.gradle"""
        gradle_file = self.gradle_path if self.gradle_path.exists() else self.gradle_kts_path

        if not gradle_file.exists():
            return {}

        try:
            content = gradle_file.read_text()
            dependencies = {}

            # Match: implementation 'group:artifact:version'
            pattern = r"(?:implementation|api|compile|testImplementation)\s+['\"]([^:'\"]+):([^:'\"]+):([^'\"]+)['\"]"

            for match in re.finditer(pattern, content):
                group = match.group(1)
                artifact = match.group(2)
                version = match.group(3)

                key = f"{group}:{artifact}"
                dependencies[key] = version

            return dependencies

        except Exception as e:
            self.logger.error(f"Failed to parse Gradle dependencies: {e}")
            return {}

    def _detect_framework(self, dependencies: Dict[str, str]) -> JavaWebFramework:
        """Detect primary web framework"""
        # Check for Spring Boot (most common)
        if any("spring-boot" in dep for dep in dependencies):
            return JavaWebFramework.SPRING_BOOT

        # Check for Spring MVC (without Boot)
        if any("spring-webmvc" in dep for dep in dependencies):
            return JavaWebFramework.SPRING_MVC

        # Check for Micronaut
        if any("micronaut" in dep for dep in dependencies):
            return JavaWebFramework.MICRONAUT

        # Check for Quarkus
        if any("quarkus" in dep for dep in dependencies):
            return JavaWebFramework.QUARKUS

        # Check for Jakarta EE / Java EE
        if any("jakarta.jakartaee-api" in dep or "javax.javaee-api" in dep for dep in dependencies):
            return JavaWebFramework.JAKARTA_EE

        # Check for Play Framework
        if any("play" in dep and "typesafe" in dep for dep in dependencies):
            return JavaWebFramework.PLAY

        # Check for Dropwizard
        if any("dropwizard" in dep for dep in dependencies):
            return JavaWebFramework.DROPWIZARD

        # Check for Vert.x
        if any("vertx" in dep for dep in dependencies):
            return JavaWebFramework.VERTX

        # Check for Spark Framework
        if any("spark-core" in dep and "sparkjava" in dep for dep in dependencies):
            return JavaWebFramework.SPARK

        # Check for Struts
        if any("struts" in dep for dep in dependencies):
            return JavaWebFramework.STRUTS

        # Check for JSF
        if any("jsf" in dep or "mojarra" in dep or "myfaces" in dep for dep in dependencies):
            return JavaWebFramework.JSF

        # Check for Vaadin
        if any("vaadin" in dep for dep in dependencies):
            return JavaWebFramework.VAADIN

        # Check for Grails
        if any("grails" in dep for dep in dependencies):
            return JavaWebFramework.GRAILS

        return JavaWebFramework.UNKNOWN

    def _get_framework_version(
        self,
        framework: JavaWebFramework,
        dependencies: Dict[str, str]
    ) -> Optional[str]:
        """Get framework version"""
        if framework == JavaWebFramework.SPRING_BOOT:
            for dep, ver in dependencies.items():
                if "spring-boot" in dep:
                    return ver
        elif framework == JavaWebFramework.MICRONAUT:
            for dep, ver in dependencies.items():
                if "micronaut-core" in dep:
                    return ver
        elif framework == JavaWebFramework.QUARKUS:
            for dep, ver in dependencies.items():
                if "quarkus-core" in dep:
                    return ver

        return None

    def _detect_web_server(self, dependencies: Dict[str, str]) -> WebServer:
        """Detect embedded web server"""
        if any("tomcat" in dep for dep in dependencies):
            return WebServer.TOMCAT
        if any("jetty" in dep for dep in dependencies):
            return WebServer.JETTY
        if any("undertow" in dep for dep in dependencies):
            return WebServer.UNDERTOW
        if any("netty" in dep for dep in dependencies):
            return WebServer.NETTY

        return WebServer.UNKNOWN

    def _get_web_server_version(
        self,
        web_server: WebServer,
        dependencies: Dict[str, str]
    ) -> Optional[str]:
        """Get web server version"""
        server_map = {
            WebServer.TOMCAT: "tomcat",
            WebServer.JETTY: "jetty",
            WebServer.UNDERTOW: "undertow",
            WebServer.NETTY: "netty"
        }

        keyword = server_map.get(web_server)
        if keyword:
            for dep, ver in dependencies.items():
                if keyword in dep:
                    return ver

        return None

    def _detect_template_engines(self, dependencies: Dict[str, str]) -> List[TemplateEngine]:
        """Detect template engines"""
        engines = []

        if any("thymeleaf" in dep for dep in dependencies):
            engines.append(TemplateEngine.THYMELEAF)
        if any("freemarker" in dep for dep in dependencies):
            engines.append(TemplateEngine.FREEMARKER)
        if any("velocity" in dep for dep in dependencies):
            engines.append(TemplateEngine.VELOCITY)
        if any("mustache" in dep for dep in dependencies):
            engines.append(TemplateEngine.MUSTACHE)
        if any("pebble" in dep for dep in dependencies):
            engines.append(TemplateEngine.PEBBLE)
        if any("groovy-templates" in dep for dep in dependencies):
            engines.append(TemplateEngine.GROOVY)

        # Check for JSP files
        if list(self.project_dir.glob("**/*.jsp")):
            engines.append(TemplateEngine.JSP)

        return engines

    def _detect_database_technologies(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect database access technologies"""
        techs = []

        if any("spring-data-jpa" in dep or "jakarta.persistence-api" in dep for dep in dependencies):
            techs.append("JPA")
        if any("hibernate" in dep for dep in dependencies):
            techs.append("Hibernate")
        if any("mybatis" in dep for dep in dependencies):
            techs.append("MyBatis")
        if any("jooq" in dep for dep in dependencies):
            techs.append("jOOQ")
        if any("jdbc" in dep for dep in dependencies):
            techs.append("JDBC")
        if any("spring-data-mongodb" in dep for dep in dependencies):
            techs.append("Spring Data MongoDB")
        if any("spring-data-redis" in dep for dep in dependencies):
            techs.append("Spring Data Redis")

        return techs

    def _detect_databases(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect database drivers"""
        dbs = []

        if any("postgresql" in dep for dep in dependencies):
            dbs.append("PostgreSQL")
        if any("mysql" in dep for dep in dependencies):
            dbs.append("MySQL")
        if any("mariadb" in dep for dep in dependencies):
            dbs.append("MariaDB")
        if any("h2" in dep for dep in dependencies):
            dbs.append("H2")
        if any("hsqldb" in dep for dep in dependencies):
            dbs.append("HSQLDB")
        if any("oracle" in dep for dep in dependencies):
            dbs.append("Oracle")
        if any("sqlserver" in dep or "mssql" in dep for dep in dependencies):
            dbs.append("SQL Server")
        if any("mongodb" in dep for dep in dependencies):
            dbs.append("MongoDB")
        if any("redis" in dep for dep in dependencies):
            dbs.append("Redis")

        return dbs

    def _detect_rest_api(self, dependencies: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Detect REST API framework"""
        if any("spring-web" in dep or "spring-webmvc" in dep for dep in dependencies):
            return True, "Spring Web"
        if any("jax-rs" in dep or "jersey" in dep or "resteasy" in dep for dep in dependencies):
            return True, "JAX-RS"
        if any("dropwizard" in dep for dep in dependencies):
            return True, "Dropwizard"

        return False, None

    def _detect_graphql(self, dependencies: Dict[str, str]) -> bool:
        """Detect GraphQL support"""
        return any("graphql" in dep for dep in dependencies)

    def _detect_soap(self, dependencies: Dict[str, str]) -> bool:
        """Detect SOAP support"""
        return any("cxf" in dep or "jax-ws" in dep or "axis" in dep for dep in dependencies)

    def _detect_security_frameworks(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect security frameworks"""
        frameworks = []

        if any("spring-security" in dep for dep in dependencies):
            frameworks.append("Spring Security")
        if any("shiro" in dep for dep in dependencies):
            frameworks.append("Apache Shiro")
        if any("keycloak" in dep for dep in dependencies):
            frameworks.append("Keycloak")

        return frameworks

    def _detect_oauth(self, dependencies: Dict[str, str]) -> bool:
        """Detect OAuth support"""
        return any("oauth" in dep for dep in dependencies)

    def _detect_jwt(self, dependencies: Dict[str, str]) -> bool:
        """Detect JWT support"""
        return any("jwt" in dep or "jjwt" in dep for dep in dependencies)

    def _detect_test_frameworks(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect testing frameworks"""
        frameworks = []

        if any("junit" in dep for dep in dependencies):
            frameworks.append("JUnit")
        if any("testng" in dep for dep in dependencies):
            frameworks.append("TestNG")
        if any("mockito" in dep for dep in dependencies):
            frameworks.append("Mockito")
        if any("rest-assured" in dep for dep in dependencies):
            frameworks.append("REST Assured")
        if any("spring-boot-starter-test" in dep for dep in dependencies):
            frameworks.append("Spring Boot Test")

        return frameworks

    def _detect_messaging(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect messaging technologies"""
        messaging = []

        if any("kafka" in dep for dep in dependencies):
            messaging.append("Apache Kafka")
        if any("rabbitmq" in dep for dep in dependencies):
            messaging.append("RabbitMQ")
        if any("activemq" in dep for dep in dependencies):
            messaging.append("ActiveMQ")
        if any("jms" in dep for dep in dependencies):
            messaging.append("JMS")

        return messaging

    def _detect_caching(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect caching technologies"""
        caching = []

        if any("redis" in dep for dep in dependencies):
            caching.append("Redis")
        if any("hazelcast" in dep for dep in dependencies):
            caching.append("Hazelcast")
        if any("ehcache" in dep for dep in dependencies):
            caching.append("EhCache")
        if any("caffeine" in dep for dep in dependencies):
            caching.append("Caffeine")

        return caching

    def _detect_config_format(self) -> str:
        """Detect configuration file format"""
        resources_dir = self.project_dir / "src" / "main" / "resources"

        if (resources_dir / "application.yml").exists() or (resources_dir / "application.yaml").exists():
            return "YAML"
        if (resources_dir / "application.properties").exists():
            return "Properties"
        if (resources_dir / "application.conf").exists():
            return "HOCON"

        return "Unknown"

    def _detect_architecture(self) -> tuple[bool, bool, List[str]]:
        """Detect microservices vs monolith architecture"""
        # Check for multi-module Maven/Gradle project
        modules = []

        if self.pom_path.exists():
            try:
                tree = ET.parse(self.pom_path)
                root = tree.getroot()
                ns = {"mvn": "http://maven.apache.org/POM/4.0.0"}

                for module in root.findall(".//mvn:modules/mvn:module", ns):
                    if module.text:
                        modules.append(module.text)
            except:
                pass

        # Check for microservices indicators
        is_microservices = (
            len(modules) > 1 or
            (self.project_dir / "docker-compose.yml").exists() or
            (self.project_dir / "kubernetes").exists() or
            list(self.project_dir.glob("**/Dockerfile"))
        )

        is_monolith = not is_microservices

        return is_microservices, is_monolith, modules


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Java Web Framework Detector and Analyzer"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Java project directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Create detector
    detector = JavaWebFrameworkDetector(project_dir=args.project_dir)

    # Analyze project
    analysis = detector.analyze()

    # Output results
    if args.json:
        import json
        result = {
            "framework": analysis.primary_framework.value,
            "framework_version": analysis.framework_version,
            "web_server": analysis.web_server.value,
            "web_server_version": analysis.web_server_version,
            "build_system": analysis.build_system,
            "template_engines": [e.value for e in analysis.template_engines],
            "database_technologies": analysis.database_technologies,
            "databases": analysis.databases,
            "has_rest_api": analysis.has_rest_api,
            "rest_framework": analysis.rest_framework,
            "has_graphql": analysis.has_graphql,
            "security_frameworks": analysis.security_frameworks,
            "test_frameworks": analysis.test_frameworks,
            "architecture": "Microservices" if analysis.is_microservices else "Monolith"
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Java Web Framework Analysis")
        print(f"{'='*60}")
        print(f"Framework:     {analysis.primary_framework.value}")
        if analysis.framework_version:
            print(f"Version:       {analysis.framework_version}")
        print(f"Build System:  {analysis.build_system}")
        print(f"Web Server:    {analysis.web_server.value}")
        if analysis.web_server_version:
            print(f"Server Version: {analysis.web_server_version}")

        if analysis.template_engines:
            print(f"Templates:     {', '.join(e.value for e in analysis.template_engines)}")

        if analysis.database_technologies:
            print(f"Data Access:   {', '.join(analysis.database_technologies)}")

        if analysis.databases:
            print(f"Databases:     {', '.join(analysis.databases)}")

        if analysis.has_rest_api:
            print(f"REST API:      Yes ({analysis.rest_framework})")

        if analysis.has_graphql:
            print(f"GraphQL:       Yes")

        if analysis.security_frameworks:
            print(f"Security:      {', '.join(analysis.security_frameworks)}")

        if analysis.test_frameworks:
            print(f"Testing:       {', '.join(analysis.test_frameworks)}")

        print(f"Architecture:  {'Microservices' if analysis.is_microservices else 'Monolith'}")

        if analysis.modules:
            print(f"Modules:       {', '.join(analysis.modules)}")

        print(f"{'='*60}\n")
