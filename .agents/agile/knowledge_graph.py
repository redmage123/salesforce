#!/usr/bin/env python3
"""
Knowledge Graph for Artemis - GraphQL Interface

Implements code relationship tracking using Memgraph with GraphQL API.
Tracks files, classes, functions, dependencies, and ADRs.

Usage:
    graph = KnowledgeGraph()
    graph.add_file("auth.py", language="python")
    graph.add_dependency("api.py", "auth.py", relationship="imports")
    impacts = graph.get_impact_analysis("auth.py", depth=3)
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

try:
    from gqlalchemy import Memgraph, Node, Relationship
    MEMGRAPH_AVAILABLE = True
except ImportError:
    MEMGRAPH_AVAILABLE = False
    print("⚠️  Warning: gqlalchemy not installed. Run: pip install gqlalchemy")


@dataclass
class CodeFile:
    """Represents a code file in the graph"""
    path: str
    language: str
    lines: int = 0
    last_modified: Optional[str] = None
    module: Optional[str] = None


@dataclass
class CodeClass:
    """Represents a class in the graph"""
    name: str
    file_path: str
    public: bool = True
    abstract: bool = False
    lines: int = 0


@dataclass
class CodeFunction:
    """Represents a function in the graph"""
    name: str
    file_path: str
    class_name: Optional[str] = None
    params: List[str] = None
    returns: Optional[str] = None
    public: bool = True
    complexity: int = 1

    def __post_init__(self):
        if self.params is None:
            self.params = []


@dataclass
class ADR:
    """Architecture Decision Record"""
    adr_id: str
    title: str
    date: str
    status: str  # proposed, accepted, rejected, deprecated, superseded
    rationale: Optional[str] = None


@dataclass
class Requirement:
    """Requirement node in knowledge graph"""
    req_id: str
    title: str
    type: str  # functional, non_functional, use_case, data, integration
    priority: str  # critical, high, medium, low
    status: str = "active"  # active, implemented, deprecated


@dataclass
class Task:
    """Task/Card node in knowledge graph"""
    card_id: str
    title: str
    priority: str
    status: str  # backlog, in_progress, review, done
    assigned_agents: List[str] = None

    def __post_init__(self):
        if self.assigned_agents is None:
            self.assigned_agents = []


@dataclass
class CodeReview:
    """Code review result node"""
    review_id: str
    card_id: str
    status: str  # PASS, FAIL
    score: int
    critical_issues: int = 0
    high_issues: int = 0


class KnowledgeGraph:
    """
    Knowledge Graph for Artemis using Memgraph with GraphQL

    Provides graph-based code analysis including:
    - Dependency tracking
    - Impact analysis
    - Architectural validation
    - Decision lineage
    - Multi-hop queries
    """

    def __init__(self, host: str = "localhost", port: int = 7687):
        """
        Initialize connection to Memgraph

        Args:
            host: Memgraph host
            port: Memgraph port (default: 7687)
        """
        if not MEMGRAPH_AVAILABLE:
            raise ImportError("gqlalchemy not installed. Run: pip install gqlalchemy")

        self.db = Memgraph(host=host, port=port)
        self._connected = False
        try:
            self._create_indexes()
            self._connected = True
        except Exception:
            # Connection failed - queries will return empty results
            pass

    def _create_indexes(self):
        """Create indexes for faster queries"""
        try:
            # Index on File.path for fast lookups
            self.db.execute("CREATE INDEX ON :File(path);")
            # Index on Class.name
            self.db.execute("CREATE INDEX ON :Class(name);")
            # Index on Function.name
            self.db.execute("CREATE INDEX ON :Function(name);")
            # Index on ADR.adr_id
            self.db.execute("CREATE INDEX ON :ADR(adr_id);")
        except Exception as e:
            # Indexes might already exist
            pass

    def query(self, cypher_query: str, params: Optional[dict] = None):
        """
        Execute a Cypher query and return results

        Args:
            cypher_query: Cypher query string
            params: Optional query parameters

        Returns:
            Query results from execute_and_fetch, or empty list if not connected

        Raises:
            Exception: If database connection fails or query times out
        """
        # Return empty results if not connected
        if not self._connected:
            return []

        try:
            results = list(self.db.execute_and_fetch(cypher_query, params or {}))
            return results
        except Exception as e:
            # Connection lost or query failed - return empty results
            # Caller (ai_query_service) will fall back to RAG
            self._connected = False
            return []

    # ==================== CREATE OPERATIONS ====================

    def add_file(self, path: str, language: str, lines: int = 0,
                 module: Optional[str] = None) -> str:
        """
        Add a code file to the graph

        Args:
            path: File path
            language: Programming language (python, javascript, etc.)
            lines: Number of lines
            module: Module/package name

        Returns:
            File path (ID)
        """
        query = """
        MERGE (f:File {path: $path})
        SET f.language = $language,
            f.lines = $lines,
            f.last_modified = $last_modified,
            f.module = $module
        RETURN f.path
        """

        result = self.db.execute_and_fetch(
            query,
            {
                "path": path,
                "language": language,
                "lines": lines,
                "last_modified": datetime.now().isoformat(),
                "module": module
            }
        )

        return path

    def add_class(self, name: str, file_path: str, public: bool = True,
                  abstract: bool = False, lines: int = 0) -> str:
        """
        Add a class to the graph

        Args:
            name: Class name
            file_path: File containing the class
            public: Is class public?
            abstract: Is class abstract?
            lines: Number of lines

        Returns:
            Class name (ID)
        """
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (c:Class {name: $name, file_path: $file_path})
        SET c.public = $public,
            c.abstract = $abstract,
            c.lines = $lines
        MERGE (f)-[:CONTAINS]->(c)
        RETURN c.name
        """

        self.db.execute_and_fetch(
            query,
            {
                "name": name,
                "file_path": file_path,
                "public": public,
                "abstract": abstract,
                "lines": lines
            }
        )

        return name

    def add_function(self, name: str, file_path: str,
                    class_name: Optional[str] = None,
                    params: Optional[List[str]] = None,
                    returns: Optional[str] = None,
                    public: bool = True,
                    complexity: int = 1) -> str:
        """
        Add a function to the graph

        Args:
            name: Function name
            file_path: File containing function
            class_name: Class name if method
            params: Parameter names
            returns: Return type
            public: Is function public?
            complexity: Cyclomatic complexity

        Returns:
            Function name (ID)
        """
        if params is None:
            params = []

        # Create function node
        query_func = """
        MATCH (f:File {path: $file_path})
        MERGE (fn:Function {name: $name, file_path: $file_path})
        SET fn.params = $params,
            fn.returns = $returns,
            fn.public = $public,
            fn.complexity = $complexity,
            fn.class_name = $class_name
        MERGE (f)-[:CONTAINS]->(fn)
        RETURN fn.name
        """

        self.db.execute_and_fetch(
            query_func,
            {
                "name": name,
                "file_path": file_path,
                "params": params,
                "returns": returns,
                "public": public,
                "complexity": complexity,
                "class_name": class_name
            }
        )

        # If method, link to class
        if class_name:
            query_method = """
            MATCH (c:Class {name: $class_name, file_path: $file_path})
            MATCH (fn:Function {name: $name, file_path: $file_path})
            MERGE (c)-[:HAS_METHOD]->(fn)
            """
            self.db.execute(
                query_method,
                {
                    "class_name": class_name,
                    "file_path": file_path,
                    "name": name
                }
            )

        return name

    def add_dependency(self, from_file: str, to_file: str,
                      relationship: str = "IMPORTS") -> None:
        """
        Add a file dependency

        Args:
            from_file: Source file
            to_file: Target file
            relationship: Type (IMPORTS, CALLS, DEPENDS_ON)
        """
        query = f"""
        MATCH (f1:File {{path: $from_file}})
        MATCH (f2:File {{path: $to_file}})
        MERGE (f1)-[r:{relationship}]->(f2)
        SET r.created = $created
        """

        self.db.execute(
            query,
            {
                "from_file": from_file,
                "to_file": to_file,
                "created": datetime.now().isoformat()
            }
        )

    def add_function_call(self, caller: str, callee: str,
                         caller_file: str, callee_file: str) -> None:
        """
        Add a function call relationship

        Args:
            caller: Calling function name
            callee: Called function name
            caller_file: File containing caller
            callee_file: File containing callee
        """
        query = """
        MATCH (fn1:Function {name: $caller, file_path: $caller_file})
        MATCH (fn2:Function {name: $callee, file_path: $callee_file})
        MERGE (fn1)-[r:CALLS]->(fn2)
        SET r.created = $created
        """

        self.db.execute(
            query,
            {
                "caller": caller,
                "callee": callee,
                "caller_file": caller_file,
                "callee_file": callee_file,
                "created": datetime.now().isoformat()
            }
        )

    def add_adr(self, adr_id: str, title: str, status: str,
                rationale: Optional[str] = None,
                impacts: Optional[List[str]] = None) -> str:
        """
        Add an Architecture Decision Record

        Args:
            adr_id: ADR identifier (e.g., "ADR-001")
            title: Decision title
            status: proposed, accepted, rejected, deprecated, superseded
            rationale: Why this decision was made
            impacts: List of file paths impacted

        Returns:
            ADR ID
        """
        query = """
        MERGE (adr:ADR {adr_id: $adr_id})
        SET adr.title = $title,
            adr.date = $date,
            adr.status = $status,
            adr.rationale = $rationale
        RETURN adr.adr_id
        """

        self.db.execute_and_fetch(
            query,
            {
                "adr_id": adr_id,
                "title": title,
                "date": datetime.now().isoformat(),
                "status": status,
                "rationale": rationale
            }
        )

        # Link to impacted files
        if impacts:
            for file_path in impacts:
                impact_query = """
                MATCH (adr:ADR {adr_id: $adr_id})
                MATCH (f:File {path: $file_path})
                MERGE (adr)-[:IMPACTS]->(f)
                """
                self.db.execute(impact_query, {"adr_id": adr_id, "file_path": file_path})

        return adr_id

    def add_requirement(self, req_id: str, title: str, type: str,
                       priority: str, status: str = "active") -> str:
        """
        Add a requirement to the graph

        Args:
            req_id: Requirement ID (e.g., "REQ-F-001")
            title: Requirement title
            type: functional, non_functional, use_case, data, integration
            priority: critical, high, medium, low
            status: active, implemented, deprecated

        Returns:
            Requirement ID
        """
        query = """
        MERGE (req:Requirement {req_id: $req_id})
        SET req.title = $title,
            req.type = $type,
            req.priority = $priority,
            req.status = $status,
            req.created = $created
        RETURN req.req_id
        """

        self.db.execute_and_fetch(
            query,
            {
                "req_id": req_id,
                "title": title,
                "type": type,
                "priority": priority,
                "status": status,
                "created": datetime.now().isoformat()
            }
        )

        return req_id

    def add_task(self, card_id: str, title: str, priority: str,
                status: str, assigned_agents: Optional[List[str]] = None) -> str:
        """
        Add a task/card to the graph

        Args:
            card_id: Card identifier
            title: Task title
            priority: high, medium, low
            status: backlog, in_progress, review, done
            assigned_agents: List of agent names

        Returns:
            Card ID
        """
        if assigned_agents is None:
            assigned_agents = []

        query = """
        MERGE (task:Task {card_id: $card_id})
        SET task.title = $title,
            task.priority = $priority,
            task.status = $status,
            task.assigned_agents = $assigned_agents,
            task.created = $created
        RETURN task.card_id
        """

        self.db.execute_and_fetch(
            query,
            {
                "card_id": card_id,
                "title": title,
                "priority": priority,
                "status": status,
                "assigned_agents": assigned_agents,
                "created": datetime.now().isoformat()
            }
        )

        return card_id

    def add_code_review(self, review_id: str, card_id: str, status: str,
                       score: int, critical_issues: int = 0,
                       high_issues: int = 0) -> str:
        """
        Add a code review result to the graph

        Args:
            review_id: Review identifier
            card_id: Associated card ID
            status: PASS or FAIL
            score: Overall score (0-100)
            critical_issues: Number of critical issues
            high_issues: Number of high severity issues

        Returns:
            Review ID
        """
        query = """
        MERGE (review:CodeReview {review_id: $review_id})
        SET review.card_id = $card_id,
            review.status = $status,
            review.score = $score,
            review.critical_issues = $critical_issues,
            review.high_issues = $high_issues,
            review.created = $created
        RETURN review.review_id
        """

        self.db.execute_and_fetch(
            query,
            {
                "review_id": review_id,
                "card_id": card_id,
                "status": status,
                "score": score,
                "critical_issues": critical_issues,
                "high_issues": high_issues,
                "created": datetime.now().isoformat()
            }
        )

        # Link review to task
        link_query = """
        MATCH (review:CodeReview {review_id: $review_id})
        MATCH (task:Task {card_id: $card_id})
        MERGE (task)-[:HAS_REVIEW]->(review)
        """
        self.db.execute(link_query, {"review_id": review_id, "card_id": card_id})

        return review_id

    def link_requirement_to_adr(self, req_id: str, adr_id: str) -> None:
        """
        Link a requirement to an ADR that addresses it

        Args:
            req_id: Requirement ID
            adr_id: ADR ID
        """
        query = """
        MATCH (req:Requirement {req_id: $req_id})
        MATCH (adr:ADR {adr_id: $adr_id})
        MERGE (adr)-[:ADDRESSES]->(req)
        SET adr.last_updated = $updated
        """

        self.db.execute(
            query,
            {
                "req_id": req_id,
                "adr_id": adr_id,
                "updated": datetime.now().isoformat()
            }
        )

    def link_requirement_to_task(self, req_id: str, card_id: str) -> None:
        """
        Link a requirement to a task

        Args:
            req_id: Requirement ID
            card_id: Card ID
        """
        query = """
        MATCH (req:Requirement {req_id: $req_id})
        MATCH (task:Task {card_id: $card_id})
        MERGE (task)-[:IMPLEMENTS]->(req)
        """

        self.db.execute(query, {"req_id": req_id, "card_id": card_id})

    def link_adr_to_file(self, adr_id: str, file_path: str,
                        relationship: str = "IMPLEMENTED_BY") -> None:
        """
        Link an ADR to files that implement it

        Args:
            adr_id: ADR ID
            file_path: File path
            relationship: IMPLEMENTED_BY, IMPACTS, DEPENDS_ON
        """
        query = f"""
        MATCH (adr:ADR {{adr_id: $adr_id}})
        MATCH (f:File {{path: $file_path}})
        MERGE (adr)-[r:{relationship}]->(f)
        SET r.created = $created
        """

        self.db.execute(
            query,
            {
                "adr_id": adr_id,
                "file_path": file_path,
                "created": datetime.now().isoformat()
            }
        )

    def link_task_to_file(self, card_id: str, file_path: str) -> None:
        """
        Link a task to files it modified

        Args:
            card_id: Card ID
            file_path: File path
        """
        query = """
        MATCH (task:Task {card_id: $card_id})
        MATCH (f:File {path: $file_path})
        MERGE (task)-[:MODIFIED]->(f)
        """

        self.db.execute(query, {"card_id": card_id, "file_path": file_path})

    # ==================== QUERY OPERATIONS (GraphQL-style) ====================

    def get_file(self, path: str) -> Optional[Dict]:
        """
        Get file details (GraphQL-style query)

        Args:
            path: File path

        Returns:
            File data or None
        """
        query = """
        MATCH (f:File {path: $path})
        RETURN f.path as path,
               f.language as language,
               f.lines as lines,
               f.module as module,
               f.last_modified as last_modified
        """

        results = list(self.db.execute_and_fetch(query, {"path": path}))
        return results[0] if results else None

    def get_impact_analysis(self, file_path: str, depth: int = 3) -> List[Dict]:
        """
        Analyze what depends on this file (GraphQL-style)

        Args:
            file_path: File to analyze
            depth: How many levels deep to traverse

        Returns:
            List of dependent files with distance
        """
        query = f"""
        MATCH path = (f:File {{path: $file_path}})<-[:IMPORTS|CALLS|DEPENDS_ON*1..{depth}]-(dependent:File)
        RETURN DISTINCT dependent.path as dependent_path,
               dependent.language as language,
               dependent.module as module,
               length(path) as distance
        ORDER BY distance
        """

        results = list(self.db.execute_and_fetch(query, {"file_path": file_path}))
        return results

    def get_circular_dependencies(self) -> List[Dict]:
        """
        Find all circular dependencies (GraphQL-style)

        Returns:
            List of cycles
        """
        query = """
        MATCH path = (f:File)-[:IMPORTS*]->(f)
        WHERE length(path) > 1
        RETURN [node in nodes(path) | node.path] as cycle,
               length(path) as cycle_length
        ORDER BY cycle_length
        """

        results = list(self.db.execute_and_fetch(query))
        return results

    def get_untested_functions(self) -> List[Dict]:
        """
        Find functions without test coverage (GraphQL-style)

        Returns:
            List of untested public functions
        """
        query = """
        MATCH (fn:Function)
        WHERE fn.public = true
        AND NOT EXISTS((t:Test)-[:COVERS]->(fn))
        RETURN fn.name as function_name,
               fn.file_path as file_path,
               fn.complexity as complexity
        ORDER BY fn.complexity DESC
        """

        results = list(self.db.execute_and_fetch(query))
        return results

    def get_decision_lineage(self, adr_id: str) -> List[Dict]:
        """
        Get decision chain for an ADR (GraphQL-style)

        Args:
            adr_id: ADR identifier

        Returns:
            Chain of related decisions
        """
        query = """
        MATCH path = (adr:ADR {adr_id: $adr_id})<-[:INFLUENCED_BY*]-(related:ADR)
        RETURN [node in nodes(path) | {
            adr_id: node.adr_id,
            title: node.title,
            status: node.status
        }] as decision_chain
        """

        results = list(self.db.execute_and_fetch(query, {"adr_id": adr_id}))
        return results[0]["decision_chain"] if results else []

    def get_architectural_violations(self, forbidden_patterns: List[tuple]) -> List[Dict]:
        """
        Find architectural violations (GraphQL-style)

        Args:
            forbidden_patterns: List of (from_module, to_module) tuples

        Returns:
            List of violations
        """
        violations = []

        for from_module, to_module in forbidden_patterns:
            query = """
            MATCH (f1:File {module: $from_module})-[:IMPORTS]->(f2:File {module: $to_module})
            RETURN f1.path as violator,
                   f2.path as forbidden_import,
                   $from_module as from_module,
                   $to_module as to_module
            """

            results = list(self.db.execute_and_fetch(
                query,
                {"from_module": from_module, "to_module": to_module}
            ))
            violations.extend(results)

        return violations

    def get_file_dependencies(self, file_path: str) -> Dict[str, List[str]]:
        """
        Get all dependencies for a file (GraphQL-style)

        Args:
            file_path: File to query

        Returns:
            Dict with imports, calls, depends_on
        """
        # Get imports
        imports_query = """
        MATCH (f:File {path: $file_path})-[:IMPORTS]->(imported:File)
        RETURN imported.path as path
        """

        imports = [r["path"] for r in self.db.execute_and_fetch(
            imports_query, {"file_path": file_path}
        )]

        # Get reverse dependencies
        imported_by_query = """
        MATCH (f:File {path: $file_path})<-[:IMPORTS]-(importer:File)
        RETURN importer.path as path
        """

        imported_by = [r["path"] for r in self.db.execute_and_fetch(
            imported_by_query, {"file_path": file_path}
        )]

        return {
            "imports": imports,
            "imported_by": imported_by
        }

    # ==================== GRAPHQL MUTATION-STYLE OPERATIONS ====================

    def update_file_metrics(self, file_path: str, lines: int,
                           complexity: Optional[int] = None) -> bool:
        """
        Update file metrics (GraphQL mutation-style)

        Args:
            file_path: File to update
            lines: New line count
            complexity: Average complexity

        Returns:
            Success status
        """
        query = """
        MATCH (f:File {path: $file_path})
        SET f.lines = $lines,
            f.last_modified = $last_modified
        RETURN f.path
        """

        params = {
            "file_path": file_path,
            "lines": lines,
            "last_modified": datetime.now().isoformat()
        }

        if complexity is not None:
            query = query.replace(
                "f.last_modified = $last_modified",
                "f.last_modified = $last_modified, f.complexity = $complexity"
            )
            params["complexity"] = complexity

        results = list(self.db.execute_and_fetch(query, params))
        return len(results) > 0

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file and all its relationships (GraphQL mutation-style)

        Args:
            file_path: File to delete

        Returns:
            Success status
        """
        query = """
        MATCH (f:File {path: $file_path})
        DETACH DELETE f
        """

        self.db.execute(query, {"file_path": file_path})
        return True

    # ==================== UTILITY OPERATIONS ====================

    def clear_all(self) -> None:
        """Clear entire graph (DANGEROUS - use only for testing)"""
        self.db.execute("MATCH (n) DETACH DELETE n")

    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get graph statistics

        Returns:
            Dict with node and relationship counts
        """
        stats = {}

        # Count files
        files_query = "MATCH (f:File) RETURN count(f) as count"
        stats["files"] = list(self.db.execute_and_fetch(files_query))[0]["count"]

        # Count classes
        classes_query = "MATCH (c:Class) RETURN count(c) as count"
        stats["classes"] = list(self.db.execute_and_fetch(classes_query))[0]["count"]

        # Count functions
        functions_query = "MATCH (fn:Function) RETURN count(fn) as count"
        stats["functions"] = list(self.db.execute_and_fetch(functions_query))[0]["count"]

        # Count relationships
        rels_query = "MATCH ()-[r]->() RETURN count(r) as count"
        stats["relationships"] = list(self.db.execute_and_fetch(rels_query))[0]["count"]

        return stats

    def export_to_json(self, output_path: str) -> None:
        """
        Export graph to JSON

        Args:
            output_path: Where to save JSON
        """
        export_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN collect(DISTINCT n) as nodes,
               collect(DISTINCT {type: type(r), from: id(n), to: id(m)}) as edges
        """

        result = list(self.db.execute_and_fetch(export_query))[0]

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)


# Example usage
if __name__ == "__main__":
    # Initialize knowledge graph
    graph = KnowledgeGraph(host="localhost", port=7687)

    print("🔧 Testing Knowledge Graph with GraphQL-style operations\n")

    # Add files
    print("Adding files...")
    graph.add_file("auth.py", "python", lines=250, module="api")
    graph.add_file("database.py", "python", lines=180, module="data")
    graph.add_file("api.py", "python", lines=320, module="api")

    # Add dependencies
    print("Adding dependencies...")
    graph.add_dependency("api.py", "auth.py", "IMPORTS")
    graph.add_dependency("api.py", "database.py", "IMPORTS")
    graph.add_dependency("auth.py", "database.py", "IMPORTS")

    # Add classes and functions
    print("Adding classes and functions...")
    graph.add_class("UserService", "auth.py", public=True, lines=80)
    graph.add_function("login", "auth.py", class_name="UserService",
                      params=["username", "password"], returns="Token")

    # Query impact analysis (GraphQL-style)
    print("\n📊 Impact Analysis for database.py:")
    impacts = graph.get_impact_analysis("database.py", depth=2)
    for impact in impacts:
        print(f"  - {impact['dependent_path']} (distance: {impact['distance']})")

    # Get file dependencies (GraphQL-style)
    print("\n🔗 Dependencies for api.py:")
    deps = graph.get_file_dependencies("api.py")
    print(f"  Imports: {deps['imports']}")
    print(f"  Imported by: {deps['imported_by']}")

    # Get stats
    print("\n📈 Graph Statistics:")
    stats = graph.get_graph_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ Knowledge Graph test complete!")
