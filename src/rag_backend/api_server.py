"""
Flask API Server for Revenue Intelligence RAG Demo

Runs from Jupyter notebook to serve the interactive HTML demo
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from vector_db import RevenueRAG

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for local development

# Global RAG system instance
rag_system = None

def init_rag_system():
    """Initialize the RAG system"""
    global rag_system
    if rag_system is None:
        print("Initializing RAG system...")
        rag_system = RevenueRAG()
        rag_system.load_and_index_data()
        print("✓ RAG system ready")
    return rag_system

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Revenue Intelligence API is running'})

@app.route('/query', methods=['POST'])
def query():
    """
    Main query endpoint for the RAG system

    Expects JSON: { "query": "user question" }
    Returns JSON: { "response": "AI answer", "sources": [...] }
    """
    try:
        data = request.json
        user_query = data.get('query', '')

        if not user_query:
            return jsonify({'error': 'No query provided'}), 400

        # Get RAG context
        rag = init_rag_system()
        context = rag.get_context_for_llm(user_query)

        # Generate response using LLM
        # For now, using rule-based system. Will add OpenAI integration next
        response = generate_response(user_query, context, rag)

        return jsonify({
            'response': response,
            'sources': extract_sources(context)
        })

    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({'error': str(e)}), 500

def generate_response(query: str, context: str, rag: RevenueRAG) -> str:
    """
    Generate response using context from RAG

    TODO: Replace with OpenAI/Claude API call
    For now, using enhanced rule-based system with actual data
    """
    query_lower = query.lower()
    results = rag.query(query, n_results=5)

    # At-risk deals query
    if 'at-risk' in query_lower or 'at risk' in query_lower or 'risk' in query_lower:
        opportunities = results['opportunities']
        response_parts = ["Based on AI analysis, here are the top at-risk opportunities:\n\n"]

        for i, (doc, meta) in enumerate(zip(opportunities['documents'][:3], opportunities['metadatas'][:3])):
            response_parts.append(f"🔴 <strong>{meta['name']}</strong><br>")
            response_parts.append(f"• AI Score: {meta['ai_score']}%<br>")
            response_parts.append(f"• Risk Level: {meta['risk_level']}<br>")
            response_parts.append(f"• Amount: ${int(meta['amount']):,}<br>")
            response_parts.append(f"• Stage: {meta['stage']}<br><br>")

        response_parts.append(f"<strong>Recommendation:</strong> Focus on these {len(opportunities['documents'][:3])} opportunities for immediate intervention.")
        return ''.join(response_parts)

    # Forecast query
    elif 'forecast' in query_lower or 'revenue' in query_lower or 'q4' in query_lower:
        # Calculate from actual data
        insights = results['insights']
        forecast_insight = None
        for doc, meta in zip(insights['documents'], insights['metadatas']):
            if meta['type'] == 'forecast':
                forecast_insight = doc
                break

        if forecast_insight:
            return f"Here's your revenue forecast based on AI analysis:<br><br>{forecast_insight}<br><br><strong>Key Insights from RAG:</strong><br>• Leveraging real opportunity data with AI scoring<br>• Confidence based on historical win rates<br>• Weighted by deal probability"

    # Priority/focus query
    elif 'prioritize' in query_lower or 'focus' in query_lower or 'priority' in query_lower:
        opportunities = results['opportunities']
        high_value = [m for m in opportunities['metadatas'] if int(m['amount']) > 500000]

        response = "Based on AI scoring and deal value, here are your priorities:<br><br>"
        response += f"<strong>1. High-Value Opportunities:</strong> Found {len(high_value)} deals >$500K<br>"

        if high_value:
            top_deal = high_value[0]
            response += f"• Top Priority: {top_deal['name']} (${int(top_deal['amount']):,}, {top_deal['ai_score']}% score)<br><br>"

        response += "<strong>2. At-Risk Deals:</strong> Deals with low AI scores need immediate attention<br>"
        response += "<strong>3. Stuck Deals:</strong> Opportunities in the same stage for extended periods<br><br>"

        response += "💡 <strong>Tip:</strong> Use the RAG system to dig deeper into specific deals!"
        return response

    # Competitive query
    elif 'competitive' in query_lower or 'competitor' in query_lower:
        insights = results['insights']
        competitive_insights = [doc for doc, meta in zip(insights['documents'], insights['metadatas'])
                               if meta['type'] == 'competitive']

        response = "Competitive Intelligence Analysis:<br><br>"
        response += "<strong>Win Rates by Competitor (from actual data):</strong><br>"

        for insight in competitive_insights:
            response += f"• {insight}<br>"

        response += "<br><strong>Recommendations:</strong><br>"
        response += "🎯 Focus on differentiation in competitive deals<br>"
        response += "💪 Leverage product specialists for technical wins<br>"
        response += "📊 Use ROI calculator to justify premium pricing"

        return response

    # Default response with context
    else:
        # Use the top opportunities from RAG results
        opportunities = results['opportunities']

        response = f"I found relevant information about your pipeline:<br><br>"

        if opportunities['documents']:
            response += "<strong>Top Relevant Opportunities:</strong><br>"
            for doc, meta in zip(opportunities['documents'][:2], opportunities['metadatas'][:2]):
                response += f"• {meta['name']}: {meta['stage']}, ${int(meta['amount']):,}<br>"

        response += "<br>💡 Try asking about:<br>"
        response += "• At-risk deals<br>"
        response += "• Revenue forecast<br>"
        response += "• Deal prioritization<br>"
        response += "• Competitive intelligence"

        return response

def extract_sources(context: str) -> list:
    """Extract source information from context"""
    # Simple extraction - in production would be more sophisticated
    return [
        {'type': 'opportunities', 'count': context.count('Stage:')},
        {'type': 'insights', 'count': context.count('AI Insights')},
        {'type': 'activities', 'count': context.count('Recent Activities')}
    ]

def start_server(port=5000, debug=False):
    """Start the Flask server"""
    print(f"\n🚀 Starting Revenue Intelligence API Server on http://localhost:{port}")
    print(f"   Health check: http://localhost:{port}/health")
    print(f"   Query endpoint: http://localhost:{port}/query")
    print("\n   Press Ctrl+C to stop the server\n")

    init_rag_system()
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    start_server()
