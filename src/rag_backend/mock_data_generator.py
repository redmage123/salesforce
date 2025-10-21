"""
Mock Data Generator for Revenue Intelligence RAG System

Generates comprehensive mock data including:
- Opportunities with detailed attributes
- Accounts with history
- Activities and interactions
- AI insights and recommendations
- Sales rep performance data
- Competitive intelligence
"""

import random
import json
from datetime import datetime, timedelta
from faker import Faker

# Set seeds for reproducibility
random.seed(42)
fake = Faker()
Faker.seed(42)

# Configuration
NUM_ACCOUNTS = 100
NUM_OPPORTUNITIES = 500
NUM_ACTIVITIES = 2000
NUM_REPS = 20

# Data constants
INDUSTRIES = ['Technology', 'Healthcare', 'Financial Services', 'Manufacturing', 'Retail', 'Energy', 'Telecommunications', 'Media']
PRODUCTS = ['Enterprise Cloud', 'Analytics Platform', 'AI Suite', 'Security Solution', 'Integration Hub', 'Data Warehouse', 'CRM Platform']
COMPETITORS = ['CompetitorA', 'CompetitorB', 'CompetitorC', 'None']
SALES_STAGES = ['Prospecting', 'Discovery', 'Solution Design', 'Negotiation', 'Closed Won', 'Closed Lost']
ACTIVITY_TYPES = ['Email', 'Call', 'Meeting', 'Demo', 'Proposal Sent', 'Contract Review', 'Executive Briefing']
SENTIMENTS = ['Positive', 'Neutral', 'Negative']

def generate_accounts():
    """Generate mock account data"""
    accounts = []
    for i in range(NUM_ACCOUNTS):
        company_name = fake.company()
        accounts.append({
            'id': f'001XX{i:06d}',
            'name': company_name,
            'industry': random.choice(INDUSTRIES),
            'annual_revenue': random.randint(1_000_000, 500_000_000),
            'employees': random.randint(50, 10000),
            'created_date': fake.date_between(start_date='-3y', end_date='-1y').isoformat(),
            'health_score': random.randint(30, 95),
            'description': f"{company_name} is a {random.choice(INDUSTRIES).lower()} company specializing in {fake.bs()}."
        })
    return accounts

def generate_opportunities(accounts):
    """Generate mock opportunity data"""
    opportunities = []
    for i in range(NUM_OPPORTUNITIES):
        account = random.choice(accounts)
        stage = random.choice(SALES_STAGES)
        is_closed = stage in ['Closed Won', 'Closed Lost']
        is_won = stage == 'Closed Won'

        close_date = fake.date_between(start_date='-6m', end_date='+6m')
        created_date = close_date - timedelta(days=random.randint(30, 180))

        # AI scoring
        base_score = random.uniform(5, 95)
        if stage == 'Closed Won':
            ai_score = random.uniform(70, 98)
        elif stage == 'Closed Lost':
            ai_score = random.uniform(2, 30)
        else:
            ai_score = base_score

        amount = random.randint(10_000, 5_000_000)
        days_in_stage = random.randint(1, 90)
        days_since_activity = random.randint(0, 45)

        # Risk level
        if ai_score < 25:
            risk_level = 'High Risk'
        elif ai_score < 50:
            risk_level = 'Medium Risk'
        elif ai_score < 75:
            risk_level = 'Low Risk'
        else:
            risk_level = 'On Track'

        product = random.choice(PRODUCTS)
        competitor = random.choice(COMPETITORS)

        # Generate insights
        insights = []
        if ai_score < 50:
            insights.append(f"AI Score of {ai_score:.1f}% indicates elevated risk")
        if days_since_activity > 14:
            insights.append(f"No activity in {days_since_activity} days - needs immediate attention")
        if days_in_stage > 30:
            insights.append(f"Stuck in {stage} for {days_in_stage} days")
        if competitor != 'None':
            insights.append(f"Facing competition from {competitor}")

        opportunities.append({
            'id': f'006XX{i:06d}',
            'account_id': account['id'],
            'account_name': account['name'],
            'name': f"{account['name']} - {product}",
            'stage': stage,
            'amount': amount,
            'close_date': close_date.isoformat(),
            'created_date': created_date.isoformat(),
            'days_in_stage': days_in_stage,
            'product': product,
            'competitor': competitor,
            'is_closed': is_closed,
            'is_won': is_won,
            'ai_score': round(ai_score, 1),
            'risk_level': risk_level,
            'days_since_activity': days_since_activity,
            'total_activities': random.randint(0, 50),
            'insights': insights,
            'description': f"Opportunity to sell {product} to {account['name']}. Current stage: {stage}. {' '.join(insights[:2]) if insights else 'Deal progressing normally.'}"
        })
    return opportunities

def generate_activities(opportunities):
    """Generate mock activity data"""
    activities = []
    for i in range(NUM_ACTIVITIES):
        opp = random.choice(opportunities)
        created_dt = datetime.fromisoformat(opp['created_date'])
        activity_date = fake.date_between(start_date=created_dt, end_date='today')
        activity_type = random.choice(ACTIVITY_TYPES)
        sentiment = random.choice(SENTIMENTS)

        # Generate realistic notes based on activity type
        if activity_type == 'Call':
            notes = f"Phone call with {fake.name()} to discuss {opp['product']} implementation timeline and pricing."
        elif activity_type == 'Meeting':
            notes = f"Meeting with stakeholders to review {opp['product']} capabilities and address technical questions."
        elif activity_type == 'Demo':
            notes = f"Product demonstration of {opp['product']} features. {fake.sentence()}"
        elif activity_type == 'Proposal Sent':
            notes = f"Sent proposal for ${opp['amount']:,} {opp['product']} solution."
        else:
            notes = fake.sentence()

        activities.append({
            'id': f'00TXX{i:06d}',
            'opportunity_id': opp['id'],
            'opportunity_name': opp['name'],
            'type': activity_type,
            'date': activity_date.isoformat(),
            'duration': random.randint(5, 120),
            'sentiment': sentiment,
            'notes': notes,
            'description': f"{activity_type} on {activity_date.isoformat()}: {notes}"
        })
    return activities

def generate_sales_reps():
    """Generate sales rep performance data"""
    reps = []
    for i in range(NUM_REPS):
        win_rate = random.uniform(0.15, 0.65)
        avg_deal_size = random.randint(100_000, 2_000_000)
        pipeline = random.randint(5_000_000, 25_000_000)

        reps.append({
            'id': f'rep_{i+1}',
            'name': fake.name(),
            'win_rate': round(win_rate, 2),
            'avg_deal_size': avg_deal_size,
            'pipeline_value': pipeline,
            'deals_count': random.randint(20, 100),
            'avg_cycle_days': random.randint(30, 120),
            'description': f"Sales rep with {win_rate*100:.0f}% win rate, ${avg_deal_size:,} average deal size, managing ${pipeline:,} in pipeline."
        })
    return reps

def generate_insights(opportunities):
    """Generate AI-powered insights"""
    insights = []

    # Top at-risk deals
    at_risk = [o for o in opportunities if o['risk_level'] == 'High Risk' and not o['is_closed']]
    at_risk_sorted = sorted(at_risk, key=lambda x: x['amount'], reverse=True)[:10]

    for opp in at_risk_sorted:
        insights.append({
            'type': 'at_risk_deal',
            'opportunity_id': opp['id'],
            'opportunity_name': opp['name'],
            'severity': 'high',
            'recommendation': f"Immediate action required for {opp['name']}. AI score: {opp['ai_score']}%. Recommend executive intervention.",
            'description': f"High-risk opportunity worth ${opp['amount']:,} with only {opp['ai_score']:.1f}% win probability. {opp['insights'][0] if opp['insights'] else 'Needs attention.'}"
        })

    # Forecast insights
    open_opps = [o for o in opportunities if not o['is_closed']]
    total_pipeline = sum(o['amount'] for o in open_opps)
    weighted_forecast = sum(o['amount'] * (o['ai_score']/100) for o in open_opps)

    insights.append({
        'type': 'forecast',
        'total_pipeline': total_pipeline,
        'expected_revenue': int(weighted_forecast),
        'confidence': 61,
        'description': f"Q4 forecast shows ${weighted_forecast:,.0f} expected revenue from ${total_pipeline:,.0f} total pipeline (61% confidence)."
    })

    # Competitive insights
    competitive_deals = [o for o in opportunities if o['competitor'] != 'None']
    by_competitor = {}
    for opp in competitive_deals:
        comp = opp['competitor']
        if comp not in by_competitor:
            by_competitor[comp] = {'won': 0, 'lost': 0, 'total': 0}
        by_competitor[comp]['total'] += 1
        if opp['is_closed']:
            if opp['is_won']:
                by_competitor[comp]['won'] += 1
            else:
                by_competitor[comp]['lost'] += 1

    for comp, stats in by_competitor.items():
        if stats['won'] + stats['lost'] > 0:
            win_rate = stats['won'] / (stats['won'] + stats['lost'])
            insights.append({
                'type': 'competitive',
                'competitor': comp,
                'win_rate': round(win_rate, 2),
                'total_deals': stats['total'],
                'description': f"Against {comp}: {win_rate*100:.0f}% win rate across {stats['total']} competitive deals."
            })

    return insights

def generate_all_data():
    """Generate all mock data and save to JSON"""
    print("Generating mock revenue intelligence data...")

    accounts = generate_accounts()
    print(f"✓ Generated {len(accounts)} accounts")

    opportunities = generate_opportunities(accounts)
    print(f"✓ Generated {len(opportunities)} opportunities")

    activities = generate_activities(opportunities)
    print(f"✓ Generated {len(activities)} activities")

    reps = generate_sales_reps()
    print(f"✓ Generated {len(reps)} sales reps")

    insights = generate_insights(opportunities)
    print(f"✓ Generated {len(insights)} AI insights")

    # Combine all data
    all_data = {
        'accounts': accounts,
        'opportunities': opportunities,
        'activities': activities,
        'sales_reps': reps,
        'insights': insights,
        'generated_at': datetime.now().isoformat()
    }

    # Save to JSON
    output_file = 'src/rag_backend/revenue_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)

    print(f"\n✅ All data saved to {output_file}")
    print(f"\nSummary:")
    print(f"  - {len(accounts)} accounts")
    print(f"  - {len(opportunities)} opportunities")
    print(f"  - {len(activities)} activities")
    print(f"  - {len(reps)} sales reps")
    print(f"  - {len(insights)} insights")

    return all_data

if __name__ == "__main__":
    generate_all_data()
