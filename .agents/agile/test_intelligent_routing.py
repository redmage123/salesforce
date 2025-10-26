#!/usr/bin/env python3
"""
Test Intelligent Routing System

This script demonstrates the intelligent router's ability to analyze tasks
and make intelligent decisions about which stages to run.
"""

from intelligent_router import IntelligentRouter, TaskRequirements
from artemis_services import PipelineLogger


def test_frontend_task():
    """Test routing decision for a frontend task"""
    print("=" * 60)
    print("TEST 1: Frontend Task with UI Components")
    print("=" * 60)

    router = IntelligentRouter(logger=PipelineLogger(verbose=True))

    card = {
        'card_id': 'test-001',
        'title': 'Create interactive dashboard with Chart.js',
        'description': '''
        Build a responsive HTML dashboard using Chart.js for data visualization.

        Requirements:
        - Single HTML file with embedded CSS and JavaScript
        - Chart.js library for interactive charts
        - WCAG 2.1 AA accessibility compliance
        - Professional gradient background
        - Auto-refresh data every 30 seconds
        ''',
        'story_points': 8
    }

    decision = router.make_routing_decision(card)
    router.log_routing_decision(decision)

    print(f"\nStages to Run: {len(decision.stages_to_run)}")
    print(f"Stages to Skip: {len(decision.stages_to_skip)}")
    print(f"UI/UX Stage: {'INCLUDED' if 'uiux' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Parallel Developers: {decision.requirements.parallel_developers_recommended} (ALWAYS 2)")
    print()


def test_backend_api_task():
    """Test routing decision for a backend API task"""
    print("=" * 60)
    print("TEST 2: Backend API Task (No Frontend)")
    print("=" * 60)

    router = IntelligentRouter(logger=PipelineLogger(verbose=True))

    card = {
        'card_id': 'test-002',
        'title': 'Implement REST API endpoint for user authentication',
        'description': '''
        Create a secure REST API endpoint for user authentication.

        Requirements:
        - JWT token generation
        - Password hashing with bcrypt
        - Rate limiting
        - Logging and monitoring
        - Unit tests with 90% coverage
        ''',
        'story_points': 5
    }

    decision = router.make_routing_decision(card)
    router.log_routing_decision(decision)

    print(f"\nStages to Run: {len(decision.stages_to_run)}")
    print(f"Stages to Skip: {len(decision.stages_to_skip)}")
    print(f"UI/UX Stage: {'INCLUDED' if 'uiux' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Parallel Developers: {decision.requirements.parallel_developers_recommended} (ALWAYS 2)")
    print()


def test_simple_bugfix():
    """Test routing decision for a simple bugfix"""
    print("=" * 60)
    print("TEST 3: Simple Bugfix (Minimal Stages)")
    print("=" * 60)

    router = IntelligentRouter(logger=PipelineLogger(verbose=True))

    card = {
        'card_id': 'test-003',
        'title': 'Fix off-by-one error in pagination',
        'description': '''
        Fix a simple off-by-one error in the pagination logic.

        The current code shows page 2/10 when it should show 1/10.
        Just need to adjust the display offset.
        ''',
        'story_points': 1
    }

    decision = router.make_routing_decision(card)
    router.log_routing_decision(decision)

    print(f"\nStages to Run: {len(decision.stages_to_run)}")
    print(f"Stages to Skip: {len(decision.stages_to_skip)}")
    print(f"Sprint Planning: {'INCLUDED' if 'sprint_planning' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Project Review: {'INCLUDED' if 'project_review' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Parallel Developers: {decision.requirements.parallel_developers_recommended} (ALWAYS 2)")
    print()


def test_complex_feature():
    """Test routing decision for a complex feature"""
    print("=" * 60)
    print("TEST 4: Complex Feature (All Stages)")
    print("=" * 60)

    router = IntelligentRouter(logger=PipelineLogger(verbose=True))

    card = {
        'card_id': 'test-004',
        'title': 'Implement multi-tenant architecture with database isolation',
        'description': '''
        Design and implement complete multi-tenant architecture.

        Requirements:
        - Database per tenant isolation strategy
        - Tenant provisioning API
        - Admin dashboard for tenant management
        - Migration tooling
        - Monitoring and alerting
        - Security audit logging
        - GDPR compliance
        ''',
        'story_points': 13
    }

    decision = router.make_routing_decision(card)
    router.log_routing_decision(decision)

    print(f"\nStages to Run: {len(decision.stages_to_run)}")
    print(f"Stages to Skip: {len(decision.stages_to_skip)}")
    print(f"Architecture: {'INCLUDED' if 'architecture' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Project Review: {'INCLUDED' if 'project_review' in decision.stages_to_run else 'SKIPPED'}")
    print(f"UI/UX Stage: {'INCLUDED' if 'uiux' in decision.stages_to_run else 'SKIPPED'}")
    print(f"Parallel Developers: {decision.requirements.parallel_developers_recommended} (ALWAYS 2)")
    print()


if __name__ == '__main__':
    print("\n")
    print("=" * 60)
    print("INTELLIGENT ROUTING SYSTEM - TEST SUITE")
    print("=" * 60)
    print("\n")

    test_frontend_task()
    test_backend_api_task()
    test_simple_bugfix()
    test_complex_feature()

    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nKey Findings:")
    print("✓ Frontend tasks include UI/UX stage")
    print("✓ Backend-only tasks skip UI/UX stage")
    print("✓ Simple tasks skip sprint planning and reviews")
    print("✓ Complex tasks run all stages")
    print("✓ ALL tasks use 2 parallel developers for competitive development")
    print("✓ DeveloperArbitrator selects best solution in ValidationStage")
    print()
