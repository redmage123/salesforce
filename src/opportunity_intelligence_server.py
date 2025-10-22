#!/usr/bin/env python3
"""
Lead/Opportunity Intelligence API Server
Flask backend for dynamic opportunity intelligence demo
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Mock data - Multiple opportunities for demo
OPPORTUNITIES = {
    "acme-corp": {
        "Id": "006xyz789",
        "Name": "Acme Corp - Enterprise Sales Cloud",
        "AccountId": "001abc456",
        "Account": {
            "Name": "Acme Corporation",
            "Industry": "Manufacturing",
            "NumberOfEmployees": 5000,
            "AnnualRevenue": 250000000
        },
        "StageName": "Proposal/Price Quote",
        "Amount": 125000,
        "CloseDate": "2025-11-30",
        "Probability": 60,
        "Type": "New Business",
        "LeadSource": "Partner Referral"
    },
    "techstart": {
        "Id": "006abc123",
        "Name": "TechStart - Marketing Cloud Implementation",
        "Account": {
            "Name": "TechStart Solutions",
            "Industry": "Technology",
            "NumberOfEmployees": 850,
            "AnnualRevenue": 45000000
        },
        "StageName": "Needs Analysis",
        "Amount": 75000,
        "CloseDate": "2025-12-15",
        "Probability": 35,
        "Type": "New Business",
        "LeadSource": "Web Inbound"
    },
    "financeco": {
        "Id": "006def456",
        "Name": "FinanceCo - Service Cloud Expansion",
        "Account": {
            "Name": "FinanceCo Banking",
            "Industry": "Financial Services",
            "NumberOfEmployees": 12000,
            "AnnualRevenue": 850000000
        },
        "StageName": "Negotiation/Review",
        "Amount": 285000,
        "CloseDate": "2025-11-15",
        "Probability": 75,
        "Type": "Existing Customer - Expansion",
        "LeadSource": "Customer Referral"
    }
}

# Activity history for each opportunity
ACTIVITIES = {
    "acme-corp": [
        # ... (abbreviated for space - would include all 15 activities from notebook)
        {
            "Id": "00T001",
            "Type": "Email",
            "Subject": "Initial outreach - Sales Cloud capabilities",
            "ActivityDate": (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d"),
            "Status": "Completed",
            "IsInbound": False,
            "ResponseReceived": True,
            "ResponseTime": "4 hours"
        },
        {
            "Id": "00T015",
            "Type": "Email",
            "Subject": "Final Proposal - Acme Corp Sales Cloud",
            "ActivityDate": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "Status": "Completed",
            "IsInbound": False,
            "ResponseReceived": False,
            "Sentiment": "Positive",
            "BuyingSignals": ["pricing approved", "executive meeting scheduled"]
        }
    ],
    "techstart": [
        {
            "Id": "00T101",
            "Type": "Call",
            "Subject": "Discovery call with Marketing Director",
            "ActivityDate": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
            "Status": "Completed",
            "IsInbound": False,
            "Sentiment": "Neutral to Positive",
            "BuyingSignals": ["budget exploration", "timeline discussed"]
        }
    ],
    "financeco": [
        {
            "Id": "00T201",
            "Type": "Meeting",
            "Subject": "Contract negotiation with Legal",
            "ActivityDate": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "Status": "Completed",
            "IsInbound": False,
            "Sentiment": "Very Positive",
            "BuyingSignals": ["contract review", "legal approval process"],
            "Concerns": ["data privacy clauses"]
        }
    ]
}

class ActivityAnalyzer:
    """Analyzes activity history to extract insights"""

    def __init__(self, activities: List[Dict]):
        self.activities = sorted(activities, key=lambda x: x['ActivityDate'])

    def get_engagement_metrics(self) -> Dict:
        """Calculate engagement metrics"""
        total_activities = len(self.activities)

        by_type = defaultdict(int)
        for activity in self.activities:
            by_type[activity['Type']] += 1

        inbound = sum(1 for a in self.activities if a.get('IsInbound', False))
        outbound = total_activities - inbound

        emails_sent = [a for a in self.activities if a['Type'] == 'Email' and not a.get('IsInbound', False)]
        responses = sum(1 for a in emails_sent if a.get('ResponseReceived', False))
        response_rate = (responses / len(emails_sent) * 100) if emails_sent else 0

        last_7_days = sum(1 for a in self.activities if
                         (datetime.now() - datetime.strptime(a['ActivityDate'], '%Y-%m-%d')).days <= 7)

        return {
            'total_activities': total_activities,
            'by_type': dict(by_type),
            'inbound': inbound,
            'outbound': outbound,
            'response_rate': round(response_rate, 1),
            'last_7_days': last_7_days,
            'engagement_level': self._calculate_engagement_level(total_activities, inbound, response_rate)
        }

    def _calculate_engagement_level(self, total: int, inbound: int, response_rate: float) -> str:
        """Determine overall engagement level"""
        score = 0
        if total >= 10: score += 2
        elif total >= 5: score += 1
        if inbound >= 4: score += 2
        elif inbound >= 2: score += 1
        if response_rate >= 75: score += 2
        elif response_rate >= 50: score += 1

        if score >= 5: return "Very High"
        elif score >= 3: return "High"
        elif score >= 2: return "Moderate"
        else: return "Low"

    def extract_buying_signals(self) -> Dict:
        """Extract and categorize buying signals"""
        all_signals = []
        concerns = []

        for activity in self.activities:
            if 'BuyingSignals' in activity:
                all_signals.extend(activity['BuyingSignals'])
            if 'Concerns' in activity:
                concerns.extend(activity['Concerns'])

        strong_signals = [
            'budget approved', 'timeline defined', 'ready for proposal',
            'firm decision date', 'pricing approved', 'executive meeting scheduled'
        ]

        strong = [s for s in all_signals if any(strong in s.lower() for strong in strong_signals)]
        moderate = [s for s in all_signals if s not in strong]

        return {
            'all_signals': all_signals,
            'strong_signals': strong,
            'moderate_signals': moderate,
            'concerns': concerns
        }

    def analyze_sentiment_trend(self) -> Dict:
        """Track sentiment over time"""
        sentiments = []

        for activity in self.activities:
            if 'Sentiment' in activity:
                sentiments.append({
                    'date': activity['ActivityDate'],
                    'sentiment': activity['Sentiment'],
                    'subject': activity['Subject']
                })

        latest = sentiments[-1]['sentiment'] if sentiments else "Unknown"

        return {
            'latest_sentiment': latest,
            'sentiment_history': sentiments,
            'trend': self._determine_trend(sentiments)
        }

    def _determine_trend(self, sentiments: List[Dict]) -> str:
        """Determine if sentiment is improving, stable, or declining"""
        if len(sentiments) < 2:
            return "Insufficient data"

        sentiment_scores = {
            'Very Positive': 5,
            'Positive': 4,
            'Neutral to Positive': 3,
            'Neutral': 2,
            'Negative': 1
        }

        recent_3 = sentiments[-3:] if len(sentiments) >= 3 else sentiments
        scores = [sentiment_scores.get(s['sentiment'], 3) for s in recent_3]

        if len(scores) >= 2:
            if scores[-1] > scores[0]: return "Improving"
            elif scores[-1] < scores[0]: return "Declining"
        return "Stable"

@app.route('/api/analyze_opportunity', methods=['POST'])
def analyze_opportunity():
    """Analyze opportunity and return comprehensive intelligence"""
    data = request.json
    opp_id = data.get('opportunity_id')

    if opp_id not in OPPORTUNITIES:
        return jsonify({'error': 'Opportunity not found'}), 404

    opportunity = OPPORTUNITIES[opp_id]
    activities = ACTIVITIES.get(opp_id, [])

    analyzer = ActivityAnalyzer(activities)
    engagement = analyzer.get_engagement_metrics()
    signals = analyzer.extract_buying_signals()
    sentiment = analyzer.analyze_sentiment_trend()

    # Calculate deal health score
    score = 0
    factors = []

    if engagement['engagement_level'] == 'Very High':
        score += 25
        factors.append("Very high engagement")
    elif engagement['engagement_level'] == 'High':
        score += 20
        factors.append("High engagement")

    if len(signals['all_signals']) >= 10:
        score += 30
        factors.append(f"Strong buying signals ({len(signals['all_signals'])} detected)")

    if sentiment['latest_sentiment'] == 'Very Positive':
        score += 20
        factors.append("Very positive sentiment")
    elif sentiment['latest_sentiment'] == 'Positive':
        score += 15
        factors.append("Positive sentiment")

    if opportunity['StageName'] in ['Proposal/Price Quote', 'Negotiation/Review']:
        score += 25
        factors.append("Advanced stage")

    if len(signals['concerns']) > 0:
        score -= min(10, len(signals['concerns']) * 5)
        factors.append(f"{len(signals['concerns'])} concern(s) raised")

    health = "Excellent" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "At Risk"

    return jsonify({
        'opportunity': opportunity,
        'engagement': engagement,
        'signals': signals,
        'sentiment': sentiment,
        'deal_health': {
            'score': score,
            'health': health,
            'factors': factors
        },
        'activities': activities,
        'tokens': {'input': 1245, 'output': 387, 'total': 1632, 'cost': 0.0245},
        'processing_time_ms': 1850
    })

@app.route('/api/recommend_action', methods=['POST'])
def recommend_action():
    """Generate next-best action recommendation"""
    data = request.json
    opp_id = data.get('opportunity_id')

    if opp_id not in OPPORTUNITIES:
        return jsonify({'error': 'Opportunity not found'}), 404

    opportunity = OPPORTUNITIES[opp_id]
    activities = ACTIVITIES.get(opp_id, [])

    # Simulate AI recommendation based on opportunity state
    if opp_id == "acme-corp":
        recommendation = {
            "action": "Wait for Response",
            "priority": "Medium",
            "reasoning": "Sent final proposal 1 day ago. Give Jennifer time to review before following up. CFO meeting scheduled for Nov 12.",
            "suggested_timing": "Follow up on Nov 11 (day before exec meeting) if no response",
            "next_actions": [
                "Prepare for potential CFO Q&A session on Nov 12",
                "Review ROI calculator to ensure accuracy",
                "Prepare responses to common CFO objections"
            ],
            "risk_factors": [
                "Competitor HubSpot is also being evaluated",
                "Accelerated timeline may concern CFO"
            ],
            "confidence_score": 85,
            "talking_points": [
                "ROI: 28% productivity increase, 14-month payback period",
                "Risk mitigation: 3 manufacturing references available",
                "Timeline: 2-month implementation (Jan 2026 go-live)",
                "Competitive advantage: Superior mobile capabilities vs HubSpot"
            ]
        }
    elif opp_id == "techstart":
        recommendation = {
            "action": "Schedule Technical Demo",
            "priority": "High",
            "reasoning": "Discovery call revealed strong interest in marketing automation. Technical validation needed.",
            "suggested_timing": "Within 3-5 days",
            "next_actions": [
                "Prepare custom demo focusing on marketing automation workflows",
                "Identify marketing automation champion within their team",
                "Research their current martech stack for integration discussion"
            ],
            "risk_factors": [
                "Budget not yet fully approved",
                "Decision timeline unclear"
            ],
            "confidence_score": 72
        }
    else:  # financeco
        recommendation = {
            "action": "Address Legal Concerns",
            "priority": "High",
            "reasoning": "Contract in legal review. Data privacy clauses causing delay. Need to resolve to close by Nov 15.",
            "suggested_timing": "Immediately - meeting with Legal within 48 hours",
            "next_actions": [
                "Engage Salesforce Legal team for contract language review",
                "Provide standard data privacy and security documentation",
                "Offer to do joint call: our Legal + their Legal"
            ],
            "risk_factors": [
                "Data privacy concerns could delay close date",
                "Legal approval process typically 2-3 weeks"
            ],
            "confidence_score": 78
        }

    return jsonify({
        'recommendation': recommendation,
        'tokens': {'input': 892, 'output': 156, 'total': 1048, 'cost': 0.0157},
        'processing_time_ms': 1420
    })

@app.route('/api/generate_email', methods=['POST'])
def generate_email():
    """Generate contextual follow-up email"""
    data = request.json
    opp_id = data.get('opportunity_id')
    scenario = data.get('scenario', 'follow_up')

    if opp_id not in OPPORTUNITIES:
        return jsonify({'error': 'Opportunity not found'}), 404

    opportunity = OPPORTUNITIES[opp_id]

    # Generate email based on opportunity and scenario
    if opp_id == "acme-corp" and scenario == "pre_meeting":
        email = {
            "subject": "Supporting materials for Nov 12 executive meeting",
            "body": """Hi Jennifer,

I hope the final proposal we sent on Friday is helpful as you prepare for the executive committee meeting on Tuesday.

I wanted to make sure you have everything you need for a successful presentation to David and the team. I've attached a one-page executive summary that distills the key points:

• ROI: 28% productivity increase, 14-month payback
• Implementation: 2-month timeline with go-live by end of January
• Validation: Technical approval from Alex, positive reference calls
• Total investment: $125K (within approved Q4 budget)

I'm happy to join for Q&A if that would be valuable, or I can remain on standby.

Best regards,
John Smith""",
            "tone_analysis": {
                "formality": 72,
                "assertiveness": 48,
                "warmth": 65
            },
            "quality_scores": {
                "personalization": 92,
                "clarity": 88,
                "cta_strength": 85
            }
        }
    else:
        email = {
            "subject": f"Following up on {opportunity['Name']}",
            "body": f"""Hi there,

I wanted to follow up on our recent conversations about {opportunity['Name']}.

Let me know if you have any questions or would like to schedule a call to discuss next steps.

Best regards,
Sales Team""",
            "tone_analysis": {
                "formality": 65,
                "assertiveness": 42,
                "warmth": 58
            },
            "quality_scores": {
                "personalization": 68,
                "clarity": 75,
                "cta_strength": 62
            }
        }

    return jsonify({
        'email': email,
        'validation': {
            'valid': True,
            'violations': [],
            'word_count': len(email['body'].split())
        },
        'tokens': {'input': 634, 'output': 198, 'total': 832, 'cost': 0.0125},
        'processing_time_ms': 1680
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Opportunity Intelligence API'})

if __name__ == '__main__':
    print("🚀 Starting Opportunity Intelligence API Server...")
    print("📡 Server running on http://localhost:5001")
    print("🔗 Frontend should connect to this endpoint")
    print("\nAvailable endpoints:")
    print("  POST /api/analyze_opportunity")
    print("  POST /api/recommend_action")
    print("  POST /api/generate_email")
    print("  GET  /api/health")
    print("\n✅ Server ready!")
    app.run(debug=True, port=5001, host='0.0.0.0')
