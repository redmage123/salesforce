# Java Ecosystem Support for Artemis

## Overview

Artemis now has comprehensive understanding of the Java ecosystem including build systems, web frameworks, and development tools. This enables Artemis to work with Java projects as effectively as it does with Python projects.

## Capabilities

### 1. Build System Support

#### Maven
- **POM parsing and manipulation**
- **Dependency management** (add, list, tree)
- **Multi-module project support**
- **Build lifecycle execution** (compile, test, package, install, deploy)
- **Plugin detection and management**
- **Property extraction and interpolation**

**Module**: `maven_manager.py`

```python
from maven_manager import MavenManager

maven = MavenManager(project_dir="/path/to/project")

# Get project info
info = maven.get_project_info()
print(f"Project: {info.group_id}:{info.artifact_id}:{info.version}")

# Build project
result = maven.build(clean=True, skip_tests=False)

# Run tests
test_result = maven.run_tests()

# Add dependency
maven.add_dependency("org.springframework.boot", "spring-boot-starter-web", "3.2.0")
```

#### Gradle
- **Build script parsing** (Groovy and Kotlin DSL)
- **Dependency detection**
- **Multi-project build support**
- **Task execution**
- **Gradle wrapper support**
- **Android project detection**

**Module**: `gradle_manager.py`

```python
from gradle_manager import GradleManager

gradle = GradleManager(project_dir="/path/to/project")

# Get project info
info = gradle.get_project_info()
print(f"Project: {info.group}:{info.name}:{info.version}")

# Build project
result = gradle.build(task="build", clean=True)

# Run tests
test_result = gradle.run_tests()
```

### 2. Web Framework Detection

Artemis can automatically detect and analyze Java web frameworks:

**Supported Frameworks:**
- Spring Boot / Spring Framework
- Jakarta EE (formerly Java EE)
- Micronaut
- Quarkus
- Play Framework
- Dropwizard
- Vert.x
- Spark Framework
- Apache Struts
- JavaServer Faces (JSF)
- Vaadin
- Grails

**Module**: `java_web_framework_detector.py`

```python
from java_web_framework_detector import JavaWebFrameworkDetector

detector = JavaWebFrameworkDetector(project_dir="/path/to/project")
analysis = detector.analyze()

print(f"Framework: {analysis.primary_framework.value}")
print(f"Web Server: {analysis.web_server.value}")
print(f"Database: {', '.join(analysis.databases)}")
print(f"REST API: {analysis.has_rest_api}")
print(f"Architecture: {'Microservices' if analysis.is_microservices else 'Monolith'}")
```

**Detected Technologies:**
- **Web Servers**: Tomcat, Jetty, Undertow, Netty
- **Template Engines**: Thymeleaf, FreeMarker, Velocity, JSP, Mustache
- **Database Technologies**: JPA, Hibernate, MyBatis, jOOQ, JDBC
- **Databases**: PostgreSQL, MySQL, Oracle, MongoDB, Redis
- **Security**: Spring Security, Apache Shiro, OAuth, JWT
- **Messaging**: Kafka, RabbitMQ, ActiveMQ, JMS
- **Caching**: Redis, Hazelcast, EhCache, Caffeine

### 3. Spring Boot Deep Analysis

For Spring Boot applications, Artemis provides specialized analysis:

**Module**: `spring_boot_analyzer.py`

```python
from spring_boot_analyzer import SpringBootAnalyzer

analyzer = SpringBootAnalyzer(project_dir="/path/to/spring-boot-app")
analysis = analyzer.analyze()

# Application structure
print(f"Main Class: {analysis.main_application_class}")
print(f"Base Package: {analysis.base_package}")

# Layers
print(f"Controllers: {len(analysis.controllers)}")
print(f"Services: {len(analysis.services)}")
print(f"Repositories: {len(analysis.repositories)}")
print(f"Entities: {len(analysis.entities)}")

# REST API
for endpoint in analysis.rest_endpoints:
    print(f"{', '.join(endpoint.methods)} {endpoint.path}")

# Features
print(f"Actuator: {analysis.actuator_enabled}")
print(f"Security: {analysis.security_config.enabled}")
print(f"Caching: {analysis.caching_enabled}")
```

**Detected Information:**
- REST API endpoints with HTTP methods and paths
- Database configuration (URL, driver, type)
- Security setup (OAuth, JWT, Basic Auth)
- Actuator endpoints
- Template engines
- Async/Scheduled tasks
- Active Spring profiles
- Test classes and frameworks

### 4. Unified Java Ecosystem Integration

**Module**: `java_ecosystem_integration.py`

The `JavaEcosystemManager` provides a single entry point for all Java project operations:

```python
from java_ecosystem_integration import JavaEcosystemManager

manager = JavaEcosystemManager(project_dir="/path/to/java-project")

# Comprehensive analysis
analysis = manager.analyze_project()

# Access summary
for key, value in analysis.summary.items():
    print(f"{key}: {value}")

# Build project
build_result = manager.build(clean=True, skip_tests=False)

# Run tests
test_result = manager.run_tests()
```

## Integration with Test Framework Selector

The Java ecosystem integration works seamlessly with Artemis's test framework selector. For Java projects:

1. **Automatic Build System Detection**: Maven or Gradle
2. **Framework Detection**: JUnit, TestNG, Spring Boot Test
3. **Intelligent Test Execution**: Via Maven/Gradle with proper configuration

## Command-Line Usage

All modules provide CLI interfaces:

### Maven Manager
```bash
# Show project info
python maven_manager.py --project-dir /path/to/project info

# Build project
python maven_manager.py --project-dir /path/to/project build

# Run tests
python maven_manager.py --project-dir /path/to/project test

# Add dependency
python maven_manager.py --project-dir /path/to/project add-dep \
    org.springframework.boot spring-boot-starter-web 3.2.0
```

### Gradle Manager
```bash
# Show project info
python gradle_manager.py --project-dir /path/to/project info

# Build project
python gradle_manager.py --project-dir /path/to/project build

# Run tests
python gradle_manager.py --project-dir /path/to/project test
```

### Java Web Framework Detector
```bash
# Analyze framework (human-readable)
python java_web_framework_detector.py --project-dir /path/to/project

# Analyze framework (JSON)
python java_web_framework_detector.py --project-dir /path/to/project --json
```

### Spring Boot Analyzer
```bash
# Analyze Spring Boot app
python spring_boot_analyzer.py --project-dir /path/to/spring-boot-app

# JSON output
python spring_boot_analyzer.py --project-dir /path/to/spring-boot-app --json
```

### Java Ecosystem Manager
```bash
# Comprehensive analysis
python java_ecosystem_integration.py --project-dir /path/to/project analyze

# Build
python java_ecosystem_integration.py --project-dir /path/to/project build

# Test
python java_ecosystem_integration.py --project-dir /path/to/project test
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           JavaEcosystemManager                          │
│         (Unified Entry Point)                           │
└─────────┬───────────────────────────────────┬───────────┘
          │                                   │
    ┌─────▼──────┐                     ┌──────▼──────┐
    │   Maven    │                     │   Gradle    │
    │  Manager   │                     │   Manager   │
    └────────────┘                     └─────────────┘
          │                                   │
          └───────────────┬───────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │  Java Web Framework Detector   │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │   Spring Boot Analyzer         │
          │   (if Spring Boot detected)    │
          └────────────────────────────────┘
```

## Files Created

1. **maven_manager.py** - Complete Maven integration
2. **gradle_manager.py** - Complete Gradle integration
3. **java_web_framework_detector.py** - Web framework detection
4. **spring_boot_analyzer.py** - Spring Boot deep analysis
5. **java_ecosystem_integration.py** - Unified integration layer

## Use Cases for Artemis

### 1. Project Analysis
When Artemis encounters a Java project, it can now:
- Identify the build system (Maven/Gradle)
- Detect the web framework and version
- Understand the application architecture
- Map REST API endpoints
- Identify database and security setup

### 2. Automated Building
Artemis can build Java projects:
- Execute full build lifecycle
- Run clean builds
- Skip tests when needed
- Handle multi-module projects

### 3. Test Execution
Artemis can run Java tests:
- Execute all tests via Maven/Gradle
- Run specific test classes
- Run specific test methods
- Parse test results (passed/failed/skipped)

### 4. Dependency Management
Artemis can manage dependencies:
- Add new dependencies to Maven projects
- Analyze dependency tree
- Detect version conflicts

### 5. Code Generation
With deep framework understanding, Artemis can:
- Generate Spring Boot controllers
- Create JPA entities
- Add REST endpoints
- Generate test classes

## Example Workflows

### Workflow 1: Analyze Unknown Java Project
```python
manager = JavaEcosystemManager(project_dir="/path/to/project")
analysis = manager.analyze_project()

if analysis.is_spring_boot:
    print("Spring Boot application detected!")
    sb = analysis.spring_boot_analysis
    print(f"Version: {sb.spring_boot_version}")
    print(f"REST Endpoints: {len(sb.rest_endpoints)}")
```

### Workflow 2: Build and Test
```python
manager = JavaEcosystemManager(project_dir="/path/to/project")

# Build
build_result = manager.build(clean=True)
if build_result.success:
    print("Build successful!")

# Run tests
test_result = manager.run_tests()
print(f"Tests: {test_result.tests_passed}/{test_result.tests_run} passed")
```

### Workflow 3: Add Feature to Spring Boot App
```python
# Analyze existing app
analyzer = SpringBootAnalyzer(project_dir="/path/to/app")
analysis = analyzer.analyze()

# Understand current structure
print(f"Base package: {analysis.base_package}")
print(f"Existing controllers: {len(analysis.controllers)}")

# Generate new controller (Artemis can now understand where it should go)
# Add dependency if needed
manager = JavaEcosystemManager(project_dir="/path/to/app")
manager.add_dependency("org.springframework.boot", "spring-boot-starter-data-jpa", "3.2.0")

# Build and test
build_result = manager.build()
```

## Integration Points with Artemis Pipeline

1. **Project Review Stage**: Analyze Java project structure and dependencies
2. **Development Stage**: Generate Java code with proper framework understanding
3. **Testing Stage**: Execute Maven/Gradle tests
4. **Code Review**: Validate Spring Boot best practices
5. **Documentation**: Document REST API endpoints and architecture

## Future Enhancements

1. **Dependency Version Management**: Suggest dependency updates
2. **Security Scanning**: Detect vulnerable dependencies
3. **Performance Analysis**: Analyze Spring Boot metrics
4. **Code Generation**: Generate boilerplate code for detected frameworks
5. **Migration Assistance**: Help migrate between framework versions

## Summary

Artemis now has enterprise-grade Java ecosystem support, matching the capabilities it has for Python projects. This enables Artemis to:

- ✅ Understand Maven and Gradle projects
- ✅ Detect and analyze 13+ web frameworks
- ✅ Provide deep Spring Boot insights
- ✅ Build Java projects automatically
- ✅ Run tests via Maven/Gradle
- ✅ Manage dependencies
- ✅ Understand project architecture (monolith vs microservices)
- ✅ Map REST APIs, databases, and security setup

This comprehensive Java support makes Artemis a truly polyglot development assistant.
