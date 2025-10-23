#!/usr/bin/env python3
"""
Test Supervisor Agent with Phase 2 Features

Tests that the supervisor agent correctly integrates:
1. Cost tracking for LLM calls
2. Config validation at startup
3. Security sandboxing for code execution
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from supervisor_agent import SupervisorAgent
from cost_tracker import BudgetExceededError


def test_config_validation_on_startup():
    """Test that supervisor validates config at startup"""
    print("\n" + "=" * 70)
    print("TEST 1: Config Validation on Startup")
    print("=" * 70)

    # Set mock environment
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    print("\n  1. Creating supervisor with config validation...")
    supervisor = SupervisorAgent(
        card_id="test-supervisor-001",
        verbose=True,
        enable_cost_tracking=False,
        enable_sandboxing=False,
        enable_config_validation=True
    )

    print("  ✅ Supervisor created with valid configuration")

    # Test invalid config
    print("\n  2. Testing invalid config detection...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "invalid-provider"

    try:
        supervisor2 = SupervisorAgent(
            card_id="test-supervisor-002",
            verbose=False,
            enable_config_validation=True
        )
        print("  ❌ Should have raised RuntimeError")
        return False
    except RuntimeError as e:
        print(f"  ✅ Invalid config caught: {str(e)[:60]}...")

    # Restore environment
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"

    return True


def test_cost_tracking():
    """Test LLM cost tracking through supervisor"""
    print("\n" + "=" * 70)
    print("TEST 2: LLM Cost Tracking")
    print("=" * 70)

    print("\n  1. Creating supervisor with cost tracking...")
    supervisor = SupervisorAgent(
        card_id="test-supervisor-cost",
        verbose=True,
        enable_cost_tracking=True,
        enable_config_validation=False,
        enable_sandboxing=False,
        daily_budget=5.00
    )

    print(f"  ✅ Cost tracker enabled (daily budget: $5.00)")

    # Track some LLM calls
    print("\n  2. Tracking LLM calls...")

    result1 = supervisor.track_llm_call(
        model="gpt-4o",
        provider="openai",
        tokens_input=5000,
        tokens_output=2000,
        stage="development",
        purpose="developer-a"
    )

    print(f"  ✅ Call 1 tracked: ${result1['cost']:.4f}")

    result2 = supervisor.track_llm_call(
        model="claude-3-5-sonnet",
        provider="anthropic",
        tokens_input=8000,
        tokens_output=3000,
        stage="code_review",
        purpose="code-review"
    )

    print(f"  ✅ Call 2 tracked: ${result2['cost']:.4f}")

    # Test budget enforcement
    print("\n  3. Testing budget enforcement...")

    budget_exceeded = False
    try:
        for i in range(100):
            supervisor.track_llm_call(
                model="gpt-4o",
                provider="openai",
                tokens_input=10000,
                tokens_output=5000,
                stage="test",
                purpose="budget-test"
            )
    except BudgetExceededError as e:
        budget_exceeded = True
        print(f"  ✅ Budget enforcement working: {str(e)[:60]}...")

    assert budget_exceeded, "Should raise BudgetExceededError"

    # Get statistics
    print("\n  4. Getting cost statistics...")
    stats = supervisor.get_statistics()

    assert "cost_tracking" in stats, "Should have cost tracking stats"
    print(f"  ✅ Cost tracking statistics:")
    print(f"     Total calls: {stats['cost_tracking']['total_calls']}")
    print(f"     Total cost: ${stats['cost_tracking']['total_cost']:.2f}")
    print(f"     Budget exceeded: {stats['cost_tracking']['budget_exceeded_count']} times")

    # Cleanup
    Path(f"/tmp/artemis_costs_test-supervisor-cost.json").unlink(missing_ok=True)

    return True


def test_security_sandboxing():
    """Test security sandboxing through supervisor"""
    print("\n" + "=" * 70)
    print("TEST 3: Security Sandboxing")
    print("=" * 70)

    print("\n  1. Creating supervisor with sandboxing...")
    supervisor = SupervisorAgent(
        card_id="test-supervisor-sandbox",
        verbose=True,
        enable_cost_tracking=False,
        enable_config_validation=False,
        enable_sandboxing=True
    )

    print(f"  ✅ Sandbox enabled (backend: {supervisor.sandbox.backend_name})")

    # Test safe code
    print("\n  2. Executing safe code...")

    safe_code = """
print("Hello from supervisor sandbox!")
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
"""

    result = supervisor.execute_code_safely(safe_code, scan_security=False)

    assert result["success"], "Safe code should execute"
    assert "Hello from supervisor sandbox!" in result["stdout"]
    print(f"  ✅ Safe code executed successfully")
    print(f"     Execution time: {result['execution_time']:.2f}s")

    # Test dangerous code (security scan)
    print("\n  3. Testing security scanner...")

    dangerous_code = """
import os
os.system("ls /")
"""

    result = supervisor.execute_code_safely(dangerous_code, scan_security=True)

    assert not result["success"], "Dangerous code should be blocked"
    assert result["killed"], "Should be killed by security scan"
    print(f"  ✅ Security scanner blocked dangerous code")
    print(f"     Reason: {result['kill_reason']}")

    # Get statistics
    print("\n  4. Getting sandbox statistics...")
    stats = supervisor.get_statistics()

    assert "security_sandbox" in stats, "Should have sandbox stats"
    print(f"  ✅ Sandbox statistics:")
    print(f"     Backend: {stats['security_sandbox']['backend']}")
    print(f"     Blocked executions: {stats['security_sandbox']['blocked_executions']}")

    return True


def test_full_integration():
    """Test all Phase 2 features together"""
    print("\n" + "=" * 70)
    print("TEST 4: Full Phase 2 Integration")
    print("=" * 70)

    print("\n  Creating supervisor with all Phase 2 features...")
    supervisor = SupervisorAgent(
        card_id="test-supervisor-full",
        verbose=True,
        enable_cost_tracking=True,
        enable_config_validation=True,
        enable_sandboxing=True,
        daily_budget=10.00
    )

    print("\n  ✅ Supervisor initialized with:")
    print(f"     • Config validation")
    print(f"     • Cost tracking (daily budget: $10.00)")
    print(f"     • Security sandbox ({supervisor.sandbox.backend_name})")

    # Simulate pipeline operations
    print("\n  Simulating pipeline operations...")

    # Track LLM call
    print("\n  1. Tracking LLM call...")
    cost_result = supervisor.track_llm_call(
        model="gpt-4o",
        provider="openai",
        tokens_input=5000,
        tokens_output=2000,
        stage="development",
        purpose="developer-a"
    )
    print(f"     Cost: ${cost_result['cost']:.4f}")

    # Execute code safely
    print("\n  2. Executing developer code in sandbox...")
    code_result = supervisor.execute_code_safely("""
# Developer-generated code
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
""", scan_security=True)

    assert code_result["success"], "Developer code should execute"
    print(f"     ✅ Code executed: {code_result['stdout'].strip()}")

    # Print health report
    print("\n  3. Generating health report...")
    supervisor.print_health_report()

    print("\n  ✅ All Phase 2 features working together!")

    # Cleanup
    Path(f"/tmp/artemis_costs_test-supervisor-full.json").unlink(missing_ok=True)

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 SUPERVISOR AGENT - PHASE 2 INTEGRATION TESTS")
    print("=" * 70)
    print("\nTesting supervisor integration with Phase 2 features:\n")
    print("  1. Config Validation on Startup")
    print("  2. LLM Cost Tracking")
    print("  3. Security Sandboxing")
    print("  4. Full Integration")
    print()

    # Set environment for tests
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    tests = [
        ("Config Validation", test_config_validation_on_startup),
        ("Cost Tracking", test_cost_tracking),
        ("Security Sandboxing", test_security_sandboxing),
        ("Full Integration", test_full_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\n🎯 Result: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 SUPERVISOR PHASE 2 INTEGRATION COMPLETE!")
        print("\n✨ Supervisor now includes:")
        print("\n  1️⃣  Config Validation")
        print("      • Validates configuration at startup")
        print("      • Raises RuntimeError on critical errors")
        print("      • Warns on non-critical issues")
        print("\n  2️⃣  Cost Tracking")
        print("      • track_llm_call() method for LLM calls")
        print("      • Budget enforcement with exceptions")
        print("      • Cost statistics in health report")
        print("\n  3️⃣  Security Sandboxing")
        print("      • execute_code_safely() method")
        print("      • Security scanning integration")
        print("      • Sandbox statistics in health report")
        print("\n🚀 Supervisor is production-ready with Phase 2 features!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
