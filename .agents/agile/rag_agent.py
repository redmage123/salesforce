#!/usr/bin/env python3
"""
RAG Agent - Pipeline Memory & Continuous Learning

Stores all pipeline artifacts in vector database for semantic retrieval.
Enables pipeline to learn from history and continuously improve.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from debug_mixin import DebugMixin

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB not installed. RAG Agent will run in mock mode.")
    print("   Install with: pip install chromadb sentence-transformers")


@dataclass
class Artifact:
    """Pipeline artifact for storage"""
    artifact_id: str
    artifact_type: str  # research_report, adr, solution, validation, etc.
    card_id: str
    task_title: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str


class RAGAgent(DebugMixin):
    """
    RAG Agent - Pipeline Memory & Learning System

    Stores and retrieves pipeline artifacts using vector embeddings
    for semantic search and continuous learning.
    """

    ARTIFACT_TYPES = [
        "research_report",
        "project_analysis",
        "project_review",        # Project review stage quality gate
        "architecture_decision",
        "developer_solution",
        "validation_result",
        "arbitration_score",
        "integration_result",
        "testing_result",
        "issue_and_fix",
        "issue_resolution",      # Supervisor issue resolution tracking
        "supervisor_recovery",   # Supervisor recovery workflow outcomes
        "sprint_plan",           # Sprint planning with story point estimates
        "notebook_example",      # Jupyter notebook examples for demonstrations
        "code_example"           # Code examples from research stage (GitHub, HuggingFace, local)
    ]

    def __init__(self, db_path: str = "db", verbose: bool = True):
        """
        Initialize RAG Agent with database path.

        Args:
            db_path: Path to RAG database (default: 'db' relative to .agents/agile)
            verbose: Enable verbose logging
        """
        DebugMixin.__init__(self, component_name="rag")
        # Convert to absolute path if relative
        self.db_path = Path(db_path)
        if not self.db_path.is_absolute():
            # Make it relative to the script's directory
            script_dir = Path(__file__).parent
            self.db_path = script_dir / self.db_path

        self.db_path.mkdir(exist_ok=True, parents=True)
        self.verbose = verbose

        if CHROMADB_AVAILABLE:
            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            self._initialize_collections()
        else:
            self.client = None
            self.collections = {}
            self._mock_storage = {}

        self.log("RAG Agent initialized")
        self.log(f"Database path: {self.db_path}")
        self.debug_log("RAGAgent initialized", db_path=str(self.db_path), chromadb_available=CHROMADB_AVAILABLE)

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            print(f"[{timestamp}] [RAG] {message}")

    def _deserialize_metadata(self, metadata: Dict) -> Dict:
        """Convert JSON strings back to Python objects in metadata"""
        deserialized = {}
        for key, value in metadata.items():
            if isinstance(value, str) and value.startswith(('[', '{')):
                try:
                    deserialized[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    deserialized[key] = value
            else:
                deserialized[key] = value
        return deserialized

    def _initialize_collections(self):
        """Initialize ChromaDB collections for each artifact type"""
        self.collections = {}

        for artifact_type in self.ARTIFACT_TYPES:
            collection_name = artifact_type
            self.collections[artifact_type] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Storage for {artifact_type} artifacts"}
            )

        self.log(f"Initialized {len(self.collections)} collections")

    def store_artifact(
        self,
        artifact_type: str,
        card_id: str,
        task_title: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store artifact in RAG database

        Args:
            artifact_type: Type of artifact (research_report, adr, etc.)
            card_id: Card ID
            task_title: Task title
            content: Full content text
            metadata: Additional metadata

        Returns:
            Artifact ID
        """
        self.debug_trace("store_artifact", artifact_type=artifact_type, card_id=card_id)
        if artifact_type not in self.ARTIFACT_TYPES:
            self.log(f"⚠️  Unknown artifact type: {artifact_type}")
            return None

        # Generate artifact ID
        artifact_id = self._generate_artifact_id(artifact_type, card_id)

        # Create artifact
        artifact = Artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            card_id=card_id,
            task_title=task_title,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

        # Store in ChromaDB or mock storage
        if CHROMADB_AVAILABLE and self.client:
            collection = self.collections[artifact_type]

            # Prepare metadata for ChromaDB (convert lists to JSON strings)
            chromadb_metadata = {
                "card_id": card_id,
                "task_title": task_title,
                "timestamp": artifact.timestamp
            }

            # Convert lists and dicts to JSON strings for ChromaDB compatibility
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    chromadb_metadata[key] = json.dumps(value)
                elif value is None:
                    chromadb_metadata[key] = ""
                else:
                    chromadb_metadata[key] = value

            collection.add(
                ids=[artifact_id],
                documents=[content],
                metadatas=[chromadb_metadata]
            )
        else:
            # Mock storage
            if artifact_type not in self._mock_storage:
                self._mock_storage[artifact_type] = []
            self._mock_storage[artifact_type].append(asdict(artifact))

        self.log(f"✅ Stored {artifact_type}: {artifact_id}")
        return artifact_id

    def query_similar(
        self,
        query_text: str,
        artifact_types: Optional[List[str]] = None,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query for similar artifacts using semantic search

        Args:
            query_text: Query text for semantic search
            artifact_types: Types to search (None = all)
            top_k: Number of results to return
            filters: Metadata filters

        Returns:
            List of similar artifacts
        """
        self.debug_if_enabled("rag_queries", "Querying RAG", query=query_text[:50], top_k=top_k)
        if artifact_types is None:
            artifact_types = self.ARTIFACT_TYPES

        results = []

        if CHROMADB_AVAILABLE and self.client:
            # Query each collection
            for artifact_type in artifact_types:
                if artifact_type not in self.collections:
                    continue

                collection = self.collections[artifact_type]

                # Build where clause from filters
                where = filters if filters else None

                # Query
                query_results = collection.query(
                    query_texts=[query_text],
                    n_results=min(top_k, 10),
                    where=where
                )

                # Process results
                if query_results and query_results['ids']:
                    for i, artifact_id in enumerate(query_results['ids'][0]):
                        # Deserialize metadata (convert JSON strings back to lists/dicts)
                        metadata = self._deserialize_metadata(query_results['metadatas'][0][i])

                        results.append({
                            "artifact_id": artifact_id,
                            "artifact_type": artifact_type,
                            "content": query_results['documents'][0][i],
                            "metadata": metadata,
                            "distance": query_results['distances'][0][i] if 'distances' in query_results else None,
                            "similarity": 1.0 - query_results['distances'][0][i] if 'distances' in query_results else 1.0
                        })
        else:
            # Mock search - simple keyword matching
            query_lower = query_text.lower()
            for artifact_type in artifact_types:
                if artifact_type in self._mock_storage:
                    for artifact in self._mock_storage[artifact_type]:
                        if query_lower in artifact['content'].lower():
                            results.append({
                                **artifact,
                                "similarity": 0.85  # Mock similarity
                            })

        # Sort by similarity and limit
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        results = results[:top_k]

        self.log(f"🔍 Found {len(results)} similar artifacts for: {query_text[:50]}...")
        return results

    def get_recommendations(
        self,
        task_description: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Get RAG-informed recommendations based on past experience

        Args:
            task_description: Description of new task
            context: Additional context (technologies, priority, etc.)

        Returns:
            Dict with recommendations based on history
        """
        context = context or {}

        # Query for similar tasks
        similar_tasks = self.query_similar(
            query_text=task_description,
            artifact_types=["research_report", "architecture_decision", "developer_solution"],
            top_k=10
        )

        if not similar_tasks:
            return {
                "based_on_history": [],
                "recommendations": ["No similar tasks found in history"],
                "avoid": [],
                "confidence": "LOW",
                "similar_tasks_count": 0
            }

        # Extract patterns from similar tasks using comprehensions
        from collections import defaultdict

        # Track technologies using defaultdict
        technologies = defaultdict(lambda: {"count": 0, "avg_score": 0, "scores": []})
        for task in similar_tasks:
            metadata = task.get('metadata', {})
            for tech in metadata.get('technologies', []):
                technologies[tech]["count"] += 1

        # Extract success patterns using list comprehension
        success_patterns = [
            {
                "approach": task['metadata'].get('approach', 'unknown'),
                "score": task['metadata'].get('arbitration_score', 0),
                "technologies": task['metadata'].get('technologies', [])
            }
            for task in similar_tasks
            if task.get('artifact_type') == 'developer_solution'
            and task.get('metadata', {}).get('winner')
        ]

        # Extract issues using list comprehension with chain
        from itertools import chain
        issues = list(chain.from_iterable(
            task.get('metadata', {}).get('issues', [])
            for task in similar_tasks
            if task.get('artifact_type') == 'validation_result'
        ))

        # Generate recommendations using comprehensions
        # Technology recommendations
        top_techs = sorted(technologies.items(), key=lambda x: x[1]['count'], reverse=True)[:3]
        based_on = [f"Used {tech} in {data['count']} past similar tasks" for tech, data in top_techs]
        recommendations = [
            f"Consider {tech} (proven in {data['count']} similar tasks)"
            for tech, data in top_techs
            if data['count'] >= 2
        ]

        # Success pattern recommendations
        based_on.extend([
            f"{pattern['approach']} approach scored {pattern['score']}/100"
            for pattern in success_patterns[:3]
        ])

        # Issue-based avoidance using Counter
        from collections import Counter
        common_issues = Counter(issue.get('type', 'unknown') for issue in issues)
        avoid = [
            f"Watch for {issue_type} issues (found in {count} similar tasks)"
            for issue_type, count in common_issues.items()
            if count >= 2
        ]

        confidence = "HIGH" if len(similar_tasks) >= 5 else "MEDIUM" if len(similar_tasks) >= 2 else "LOW"

        return {
            "based_on_history": based_on,
            "recommendations": recommendations if recommendations else ["Insufficient history for recommendations"],
            "avoid": avoid,
            "confidence": confidence,
            "similar_tasks_count": len(similar_tasks)
        }

    def extract_patterns(
        self,
        pattern_type: str = "technology_success_rates",
        time_window_days: int = 90
    ) -> Dict:
        """
        Extract learning patterns from stored artifacts

        Args:
            pattern_type: Type of pattern to extract
            time_window_days: Time window for analysis

        Returns:
            Dict with extracted patterns
        """
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        cutoff_str = cutoff_date.isoformat()

        patterns = {}

        if pattern_type == "technology_success_rates":
            # Get all developer solutions
            solutions = self.query_similar(
                query_text="",  # Empty query to get all
                artifact_types=["developer_solution"],
                top_k=1000
            )

            # Calculate success rates per technology
            tech_stats = {}
            for solution in solutions:
                metadata = solution.get('metadata', {})

                # Check if within time window
                if metadata.get('timestamp', '') < cutoff_str:
                    continue

                technologies = metadata.get('technologies', [])
                score = metadata.get('arbitration_score', 0)
                success = metadata.get('winner', False)

                for tech in technologies:
                    if tech not in tech_stats:
                        tech_stats[tech] = {
                            "tasks_count": 0,
                            "total_score": 0,
                            "successes": 0
                        }

                    tech_stats[tech]["tasks_count"] += 1
                    tech_stats[tech]["total_score"] += score
                    if success:
                        tech_stats[tech]["successes"] += 1

            # Calculate averages and recommendations
            for tech, stats in tech_stats.items():
                if stats["tasks_count"] > 0:
                    avg_score = stats["total_score"] / stats["tasks_count"]
                    success_rate = stats["successes"] / stats["tasks_count"]

                    recommendation = "HIGHLY_RECOMMENDED" if avg_score >= 90 and success_rate >= 0.8 else \
                                     "RECOMMENDED" if avg_score >= 80 and success_rate >= 0.6 else \
                                     "CONSIDER_ALTERNATIVES"

                    patterns[tech] = {
                        "tasks_count": stats["tasks_count"],
                        "avg_score": round(avg_score, 1),
                        "success_rate": round(success_rate, 2),
                        "recommendation": recommendation
                    }

        return patterns

    def _generate_artifact_id(self, artifact_type: str, card_id: str) -> str:
        """Generate unique artifact ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique = hashlib.md5(f"{artifact_type}{card_id}{timestamp}".encode()).hexdigest()[:8]
        return f"{artifact_type}-{card_id}-{unique}"

    def get_stats(self) -> Dict:
        """Get RAG database statistics"""
        stats = {
            "total_artifacts": 0,
            "by_type": {},
            "database_path": str(self.db_path),
            "chromadb_available": CHROMADB_AVAILABLE
        }

        if CHROMADB_AVAILABLE and self.client:
            for artifact_type, collection in self.collections.items():
                count = collection.count()
                stats["by_type"][artifact_type] = count
                stats["total_artifacts"] += count
        else:
            for artifact_type, artifacts in self._mock_storage.items():
                count = len(artifacts)
                stats["by_type"][artifact_type] = count
                stats["total_artifacts"] += count

        return stats


# Convenience functions
def create_rag_agent(db_path: str = "db") -> RAGAgent:
    """
    Create RAG agent instance.

    Args:
        db_path: Path to RAG database (default: 'db' relative to .agents/agile)

    Returns:
        Initialized RAGAgent instance
    """
    return RAGAgent(db_path=db_path)


if __name__ == "__main__":
    # Example usage
    print("RAG Agent - Example Usage")
    print("=" * 60)

    # Create agent
    rag = RAGAgent()

    # Store research report
    rag.store_artifact(
        artifact_type="research_report",
        card_id="card-123",
        task_title="Add OAuth authentication",
        content="""
        Research Report: OAuth Authentication

        Recommendation: Use authlib library
        - GitHub stars: 4.3k
        - Actively maintained
        - Best documentation

        Critical finding: Must encrypt tokens in database
        """,
        metadata={
            "technologies": ["authlib", "OAuth2", "Flask"],
            "recommendations": ["Use authlib", "Encrypt tokens"],
            "confidence": "HIGH"
        }
    )

    # Store ADR
    rag.store_artifact(
        artifact_type="architecture_decision",
        card_id="card-123",
        task_title="Add OAuth authentication",
        content="""
        ADR-003: OAuth Authentication

        Decision: Use authlib + Flask-Login
        Reasoning: Based on research showing authlib is most maintained
        """,
        metadata={
            "adr_number": "003",
            "technologies": ["authlib", "Flask-Login"],
            "decision": "Use authlib"
        }
    )

    # Query similar
    print("\n📊 Querying for OAuth-related artifacts...")
    results = rag.query_similar("OAuth library selection", top_k=5)

    for result in results:
        print(f"\n  Found: {result['artifact_type']}")
        print(f"  Card: {result.get('metadata', {}).get('card_id')}")
        print(f"  Similarity: {result['similarity']:.2f}")

    # Get recommendations
    print("\n💡 Getting recommendations for new OAuth task...")
    recommendations = rag.get_recommendations(
        task_description="Add GitHub OAuth login",
        context={"technologies": ["OAuth", "GitHub"]}
    )

    print(f"\n  Based on history:")
    for item in recommendations['based_on_history']:
        print(f"    - {item}")

    print(f"\n  Recommendations:")
    for item in recommendations['recommendations']:
        print(f"    - {item}")

    # Get stats
    print("\n📈 RAG Database Statistics:")
    stats = rag.get_stats()
    print(f"  Total artifacts: {stats['total_artifacts']}")
    print(f"  By type:")
    for artifact_type, count in stats['by_type'].items():
        if count > 0:
            print(f"    - {artifact_type}: {count}")

    print("\n" + "=" * 60)
    print("✅ Example complete!")
