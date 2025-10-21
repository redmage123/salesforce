"""
Vector Database for Revenue Intelligence RAG System

Uses ChromaDB and sentence-transformers for semantic search
"""

import json
import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

class RevenueRAG:
    """Revenue Intelligence RAG System with Vector Database"""

    def __init__(self, data_path: str = 'src/rag_backend/revenue_data.json',
                 persist_dir: str = 'src/rag_backend/chroma_db'):
        """
        Initialize the RAG system

        Args:
            data_path: Path to the JSON data file
            persist_dir: Directory to persist ChromaDB
        """
        self.data_path = data_path
        self.persist_dir = persist_dir

        # Initialize embedding model
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize ChromaDB
        print("Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(path=persist_dir)

        # Create or get collections
        self.opportunities_collection = self.client.get_or_create_collection(
            name="opportunities",
            metadata={"description": "Sales opportunities"}
        )

        self.insights_collection = self.client.get_or_create_collection(
            name="insights",
            metadata={"description": "AI-generated insights"}
        )

        self.activities_collection = self.client.get_or_create_collection(
            name="activities",
            metadata={"description": "Sales activities and interactions"}
        )

        print("✓ RAG system initialized")

    def load_and_index_data(self):
        """Load data from JSON and create embeddings"""
        print("Loading revenue data...")
        with open(self.data_path, 'r') as f:
            data = json.load(f)

        self.data = data

        # Index opportunities
        print("Indexing opportunities...")
        if self.opportunities_collection.count() == 0:
            self._index_opportunities(data['opportunities'])
        else:
            print(f"  Opportunities already indexed ({self.opportunities_collection.count()} items)")

        # Index insights
        print("Indexing insights...")
        if self.insights_collection.count() == 0:
            self._index_insights(data['insights'])
        else:
            print(f"  Insights already indexed ({self.insights_collection.count()} items)")

        # Index activities
        print("Indexing activities...")
        if self.activities_collection.count() == 0:
            self._index_activities(data['activities'][:500])  # Limit to 500 for speed
        else:
            print(f"  Activities already indexed ({self.activities_collection.count()} items)")

        print("✓ Data indexed successfully")

    def _index_opportunities(self, opportunities: List[Dict]):
        """Index opportunities into vector DB"""
        ids = []
        documents = []
        metadatas = []

        for opp in opportunities:
            ids.append(opp['id'])

            # Create searchable document text
            doc_text = f"{opp['name']}. {opp['description']} "
            doc_text += f"Stage: {opp['stage']}. Product: {opp['product']}. "
            doc_text += f"Amount: ${opp['amount']:,}. AI Score: {opp['ai_score']}%. "
            doc_text += f"Risk: {opp['risk_level']}. "
            if opp['insights']:
                doc_text += ' '.join(opp['insights'])

            documents.append(doc_text)

            # Store metadata
            metadatas.append({
                'type': 'opportunity',
                'name': opp['name'],
                'stage': opp['stage'],
                'amount': str(opp['amount']),
                'ai_score': str(opp['ai_score']),
                'risk_level': opp['risk_level'],
                'competitor': opp['competitor']
            })

        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.opportunities_collection.add(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        print(f"  Indexed {len(ids)} opportunities")

    def _index_insights(self, insights: List[Dict]):
        """Index AI insights into vector DB"""
        ids = []
        documents = []
        metadatas = []

        for idx, insight in enumerate(insights):
            ids.append(f"insight_{idx}")
            documents.append(insight['description'])

            metadata = {
                'type': insight['type']
            }
            # Add type-specific metadata
            if 'opportunity_id' in insight:
                metadata['opportunity_id'] = insight['opportunity_id']
            if 'competitor' in insight:
                metadata['competitor'] = insight['competitor']

            metadatas.append(metadata)

        self.insights_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        print(f"  Indexed {len(ids)} insights")

    def _index_activities(self, activities: List[Dict]):
        """Index activities into vector DB"""
        ids = []
        documents = []
        metadatas = []

        for activity in activities:
            ids.append(activity['id'])
            documents.append(activity['description'])

            metadatas.append({
                'type': 'activity',
                'activity_type': activity['type'],
                'sentiment': activity['sentiment'],
                'opportunity_id': activity['opportunity_id']
            })

        # Add in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.activities_collection.add(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )

        print(f"  Indexed {len(ids)} activities")

    def query(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Query the RAG system with semantic search

        Args:
            query_text: User's natural language query
            n_results: Number of results to return

        Returns:
            Dict containing relevant opportunities, insights, and activities
        """
        # Search across all collections
        opp_results = self.opportunities_collection.query(
            query_texts=[query_text],
            n_results=min(n_results, self.opportunities_collection.count())
        )

        insight_results = self.insights_collection.query(
            query_texts=[query_text],
            n_results=min(3, self.insights_collection.count())
        )

        activity_results = self.activities_collection.query(
            query_texts=[query_text],
            n_results=min(3, self.activities_collection.count())
        )

        return {
            'opportunities': {
                'ids': opp_results['ids'][0],
                'documents': opp_results['documents'][0],
                'metadatas': opp_results['metadatas'][0],
                'distances': opp_results['distances'][0]
            },
            'insights': {
                'documents': insight_results['documents'][0],
                'metadatas': insight_results['metadatas'][0]
            },
            'activities': {
                'documents': activity_results['documents'][0],
                'metadatas': activity_results['metadatas'][0]
            }
        }

    def get_context_for_llm(self, query_text: str) -> str:
        """
        Get formatted context for LLM from vector DB query

        Args:
            query_text: User's query

        Returns:
            Formatted context string for LLM prompt
        """
        results = self.query(query_text, n_results=5)

        context = "## Relevant Revenue Intelligence Data:\n\n"

        # Add opportunities
        context += "### Opportunities:\n"
        for doc, meta in zip(results['opportunities']['documents'], results['opportunities']['metadatas']):
            context += f"- {doc}\n"

        # Add insights
        if results['insights']['documents']:
            context += "\n### AI Insights:\n"
            for doc in results['insights']['documents']:
                context += f"- {doc}\n"

        # Add activities (if relevant)
        if results['activities']['documents']:
            context += "\n### Recent Activities:\n"
            for doc in results['activities']['documents'][:2]:
                context += f"- {doc}\n"

        return context

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        return {
            'opportunities': self.opportunities_collection.count(),
            'insights': self.insights_collection.count(),
            'activities': self.activities_collection.count()
        }
