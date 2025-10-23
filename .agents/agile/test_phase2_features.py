#!/usr/bin/env python3
"""
Phase 2 Features Integration Test

Tests all three Phase 2 security and production-readiness features:
1. Security Sandboxing (safe code execution with resource limits)
2. Cost Management (LLM token tracking and budget controls)
3. Config Validation (fail-fast startup validation)
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from sandbox_executor import SandboxExecutor, SandboxConfig, SecurityScanner
from cost_tracker import CostTracker, BudgetExceededError, ModelPricing
from config_validator import ConfigValidator


def test_security_sandboxing():
    """Test security sandboxing with resource limits"""
    print("\n" + "=" * 70)
    print("TEST 1: Security Sandboxing")
    print("=" * 70)

    # Create sandbox with strict limits
    config = SandboxConfig(
        max_cpu_time=5,  # 5 seconds CPU
        max_memory_mb=128,  # 128 MB RAM
        timeout=10  # 10 seconds overall
    )

    executor = SandboxExecutor(config)
    print(f"  Using backend: {executor.backend_name}")

    # Test 1: Safe code execution
    print("\n  1. Testing safe code execution...")
    safe_code = """
print("Hello from sandbox!")
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
"""

    result = executor.execute_python_code(safe_code, scan_security=False)
    assert result.success, "Safe code should execute successfully"
    assert "Hello from sandbox!" in result.stdout
    assert "sqrt(16) = 4.0" in result.stdout
    print(f"    ✅ Safe code executed successfully in {result.execution_time:.2f}s")

    # Test 2: Security scanning blocks dangerous code
    print("\n  2. Testing security scanner...")
    dangerous_code = """
import os
os.system("ls /")
"""

    result = executor.execute_python_code(dangerous_code, scan_security=True)
    assert not result.success, "Dangerous code should be blocked"
    assert result.killed, "Should be killed by security scan"
    assert "Failed security scan" in result.kill_reason
    print(f"    ✅ Security scanner blocked dangerous code: {result.stderr[:80]}")

    # Test 3: Timeout enforcement
    print("\n  3. Testing timeout enforcement...")
    timeout_code = """
import time
time.sleep(20)  # Exceeds 10 second timeout
"""

    result = executor.execute_python_code(timeout_code, scan_security=False)
    assert not result.success, "Timeout code should fail"
    assert result.killed, "Should be killed by timeout"
    assert "Timeout" in result.kill_reason
    print(f"    ✅ Timeout enforced: {result.kill_reason}")

    # Test 4: Security scanner detects patterns
    print("\n  4. Testing security pattern detection...")

    scan_results = [
        ("eval('x=1')", ["eval("]),
        ("exec('print(1)')", ["exec("]),
        ("open('/etc/passwd')", ["open("]),
        ("import socket; s = socket.socket()", ["socket."]),
    ]

    for code, expected_patterns in scan_results:
        scan = SecurityScanner.scan_code(code)
        assert not scan["safe"], f"Should detect dangerous code: {code}"
        found_patterns = [issue["pattern"] for issue in scan["issues"]]
        for pattern in expected_patterns:
            assert any(pattern in p for p in found_patterns), f"Should detect pattern: {pattern}"

    print(f"    ✅ Security scanner detected all dangerous patterns")

    print("\n  ✅ Security sandboxing fully functional")
    print("    • Safe code execution with resource limits")
    print("    • Security scanning blocks dangerous patterns")
    print("    • Timeout enforcement works")
    print("    • Pattern detection comprehensive")

    return True


def test_cost_management():
    """Test LLM cost tracking and budget controls"""
    print("\n" + "=" * 70)
    print("TEST 2: Cost Management & Budget Controls")
    print("=" * 70)

    # Create tracker with budgets
    tracker = CostTracker(
        storage_path="/tmp/test_phase2_costs.json",
        daily_budget=5.00,   # $5/day
        monthly_budget=100.00  # $100/month
    )

    print(f"  Budgets: Daily=${tracker.daily_budget:.2f}, Monthly=${tracker.monthly_budget:.2f}")

    # Test 1: Cost calculation accuracy
    print("\n  1. Testing cost calculation...")

    # GPT-4o call
    gpt4o_cost = ModelPricing.get_cost("gpt-4o", 10000, 5000)
    expected_gpt4o = (10000/1_000_000 * 2.50) + (5000/1_000_000 * 10.00)
    assert abs(gpt4o_cost - expected_gpt4o) < 0.0001, "GPT-4o cost calculation incorrect"
    print(f"    ✅ GPT-4o cost: ${gpt4o_cost:.4f} (10k input + 5k output)")

    # Claude 3.5 Sonnet call
    claude_cost = ModelPricing.get_cost("claude-3-5-sonnet", 8000, 3000)
    expected_claude = (8000/1_000_000 * 3.00) + (3000/1_000_000 * 15.00)
    assert abs(claude_cost - expected_claude) < 0.0001, "Claude cost calculation incorrect"
    print(f"    ✅ Claude 3.5 cost: ${claude_cost:.4f} (8k input + 3k output)")

    # Test 2: Track calls and check daily usage
    print("\n  2. Testing call tracking...")

    # Create fresh tracker for this test
    tracker2 = CostTracker(
        storage_path="/tmp/test_phase2_costs_tracking.json",
        daily_budget=5.00
    )

    result = tracker2.track_call(
        model="gpt-4o",
        provider="openai",
        tokens_input=5000,
        tokens_output=2000,
        stage="development",
        card_id="test-card-001",
        purpose="developer-a"
    )

    assert result["cost"] > 0, "Cost should be tracked"
    assert abs(result["daily_usage"] - result["cost"]) < 0.0001, "Daily usage should equal cost for first call"
    print(f"    ✅ Call tracked: ${result['cost']:.4f}")
    print(f"       Daily usage: ${result['daily_usage']:.4f} / ${result['daily_budget']:.2f}")
    print(f"       Remaining: ${result['daily_remaining']:.4f}")

    # Cleanup
    Path("/tmp/test_phase2_costs_tracking.json").unlink(missing_ok=True)

    # Test 3: Budget enforcement (should raise exception)
    print("\n  3. Testing budget enforcement...")

    # Create fresh tracker for budget enforcement test
    tracker3 = CostTracker(
        storage_path="/tmp/test_phase2_costs_budget.json",
        daily_budget=5.00
    )

    budget_exceeded = False
    try:
        # Try to spend $10 (exceeds $5 daily budget)
        # Each call costs about $0.075, so we need ~70 calls to exceed $5
        for i in range(100):
            tracker3.track_call(
                model="gpt-4o",
                provider="openai",
                tokens_input=10000,
                tokens_output=5000,
                stage="test",
                card_id="test-card-002",
                purpose="budget-test"
            )
    except BudgetExceededError as e:
        budget_exceeded = True
        print(f"    ✅ Budget enforcement working: {str(e)[:80]}...")

    assert budget_exceeded, "Should raise BudgetExceededError when budget exceeded"

    # Cleanup
    Path("/tmp/test_phase2_costs_budget.json").unlink(missing_ok=True)

    # Test 4: Statistics and breakdown
    print("\n  4. Testing statistics and breakdown...")

    stats = tracker.get_statistics()
    assert stats["total_calls"] > 0, "Should have calls tracked"
    assert stats["total_cost"] > 0, "Should have total cost"
    assert "development" in stats["by_stage"], "Should have stage breakdown"
    assert "gpt-4o" in stats["by_model"], "Should have model breakdown"

    print(f"    ✅ Statistics generated:")
    print(f"       Total calls: {stats['total_calls']}")
    print(f"       Total cost: ${stats['total_cost']:.2f}")
    print(f"       Average cost/call: ${stats['average_cost_per_call']:.4f}")
    print(f"       Stages tracked: {list(stats['by_stage'].keys())}")
    print(f"       Models tracked: {list(stats['by_model'].keys())}")

    print("\n  ✅ Cost management fully functional")
    print("    • Accurate cost calculation per model")
    print("    • Call tracking with metadata")
    print("    • Budget enforcement (daily/monthly)")
    print("    • Comprehensive statistics")

    # Cleanup
    Path("/tmp/test_phase2_costs.json").unlink(missing_ok=True)

    return True


def test_config_validation():
    """Test fail-fast configuration validation"""
    print("\n" + "=" * 70)
    print("TEST 3: Configuration Validation")
    print("=" * 70)

    # Save original env vars
    original_provider = os.getenv("ARTEMIS_LLM_PROVIDER")
    original_api_key = os.getenv("OPENAI_API_KEY")

    # Test 1: Valid configuration
    print("\n  1. Testing valid configuration...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    # Should have some passed checks
    assert report.passed > 0, "Should have some passing checks"
    print(f"    ✅ Validation report: {report.passed} passed, {report.warnings} warnings, {report.errors} errors")
    print(f"       Overall status: {report.overall_status}")

    # Test 2: Invalid LLM provider
    print("\n  2. Testing invalid LLM provider detection...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "invalid-provider"

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    # Should have error for invalid provider
    provider_errors = [r for r in report.results if r.check_name == "LLM Provider" and not r.passed]
    assert len(provider_errors) > 0, "Should detect invalid provider"
    print(f"    ✅ Invalid provider detected: {provider_errors[0].message}")

    # Test 3: Missing API key
    print("\n  3. Testing missing API key detection...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "openai"
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    # Should have error for missing API key
    api_key_errors = [r for r in report.results if "API Key" in r.check_name and not r.passed]
    assert len(api_key_errors) > 0, "Should detect missing API key"
    print(f"    ✅ Missing API key detected: {api_key_errors[0].message}")
    if api_key_errors[0].fix_suggestion:
        print(f"       Fix suggestion: {api_key_errors[0].fix_suggestion}")

    # Test 4: File path validation
    print("\n  4. Testing file path validation...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"  # Use mock to avoid API key issues

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    # Should validate important paths
    path_checks = [r for r in report.results if r.check_name.startswith("Path:")]
    assert len(path_checks) > 0, "Should check file paths"
    passed_paths = [r for r in path_checks if r.passed]
    print(f"    ✅ Path validation: {len(passed_paths)}/{len(path_checks)} paths accessible")

    # Test 5: Resource limits validation
    print("\n  5. Testing resource limits validation...")
    os.environ["ARTEMIS_MAX_PARALLEL_DEVELOPERS"] = "3"

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    resource_checks = [r for r in report.results if "Parallel Developers" in r.check_name]
    assert len(resource_checks) > 0, "Should validate resource limits"
    print(f"    ✅ Resource limits validated")

    print("\n  ✅ Configuration validation fully functional")
    print("    • Valid configuration detection")
    print("    • Invalid provider detection")
    print("    • Missing API key detection")
    print("    • File path validation")
    print("    • Resource limits validation")

    # Restore original env vars
    if original_provider:
        os.environ["ARTEMIS_LLM_PROVIDER"] = original_provider
    elif "ARTEMIS_LLM_PROVIDER" in os.environ:
        del os.environ["ARTEMIS_LLM_PROVIDER"]

    if original_api_key:
        os.environ["OPENAI_API_KEY"] = original_api_key
    elif "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    return True


def test_integration():
    """Test all three Phase 2 features working together"""
    print("\n" + "=" * 70)
    print("TEST 4: Full Phase 2 Integration")
    print("=" * 70)

    print("\n  Simulating production-ready pipeline execution with:")
    print("    • Config validation before startup")
    print("    • Cost tracking for all LLM calls")
    print("    • Sandboxed code execution")

    # Step 1: Config validation
    print("\n  1. Validating configuration...")
    os.environ["ARTEMIS_LLM_PROVIDER"] = "mock"
    os.environ["ARTEMIS_MESSENGER_TYPE"] = "mock"

    validator = ConfigValidator(verbose=False)
    report = validator.validate_all()

    if report.overall_status == "fail":
        print("    ❌ Configuration validation failed, aborting pipeline")
        return False

    print(f"    ✅ Configuration valid ({report.overall_status})")

    # Step 2: Initialize cost tracker
    print("\n  2. Initializing cost tracker...")
    tracker = CostTracker(
        storage_path="/tmp/test_integration_costs.json",
        daily_budget=10.00
    )
    print(f"    ✅ Cost tracker ready (daily budget: ${tracker.daily_budget:.2f})")

    # Step 3: Initialize sandbox
    print("\n  3. Initializing sandbox executor...")
    config = SandboxConfig(max_cpu_time=30, max_memory_mb=256, timeout=60)
    executor = SandboxExecutor(config)
    print(f"    ✅ Sandbox ready (backend: {executor.backend_name})")

    # Step 4: Simulate pipeline stages with cost tracking
    print("\n  4. Simulating pipeline stages...")

    stages = [
        ("project_analysis", "gpt-4o", 3000, 1500),
        ("architecture", "gpt-4o", 5000, 2000),
        ("development", "claude-3-5-sonnet", 8000, 4000),
        ("code_review", "claude-3-5-sonnet", 6000, 3000),
    ]

    total_cost = 0.0
    for stage, model, input_tokens, output_tokens in stages:
        result = tracker.track_call(
            model=model,
            provider="openai" if "gpt" in model else "anthropic",
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            stage=stage,
            card_id="integration-test-001",
            purpose=stage
        )
        total_cost += result["cost"]
        print(f"       {stage}: ${result['cost']:.4f} ({model})")

    print(f"    ✅ All stages tracked: ${total_cost:.2f} total")

    # Step 5: Execute sandboxed code (simulating developer output)
    print("\n  5. Executing developer code in sandbox...")

    developer_code = """
# Simulated developer-generated code
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

result = calculate_fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""

    exec_result = executor.execute_python_code(developer_code, scan_security=True)
    assert exec_result.success, "Developer code should execute successfully"
    print(f"    ✅ Code executed successfully in {exec_result.execution_time:.2f}s")
    print(f"       Output: {exec_result.stdout.strip()}")

    # Step 6: Get final statistics
    print("\n  6. Generating final statistics...")
    stats = tracker.get_statistics()
    print(f"    ✅ Pipeline complete:")
    print(f"       Total LLM calls: {stats['total_calls']}")
    print(f"       Total cost: ${stats['total_cost']:.2f}")
    print(f"       Budget remaining: ${stats['daily_remaining']:.2f}")
    print(f"       Stages: {list(stats['by_stage'].keys())}")

    print("\n  🎉 All Phase 2 features integrated successfully!")

    # Cleanup
    Path("/tmp/test_integration_costs.json").unlink(missing_ok=True)

    return True


def main():
    """Run all Phase 2 tests"""
    print("\n" + "=" * 70)
    print("🧪 PHASE 2 FEATURES - INTEGRATION TEST SUITE")
    print("==" * 70)
    print("\nTesting production-readiness features for Artemis:\n")
    print("  1. Security Sandboxing (safe code execution)")
    print("  2. Cost Management (LLM budget controls)")
    print("  3. Config Validation (fail-fast startup)")
    print()

    tests = [
        ("Security Sandboxing", test_security_sandboxing),
        ("Cost Management", test_cost_management),
        ("Config Validation", test_config_validation),
        ("Full Integration", test_integration),
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
        print("\n🎉 PHASE 2 COMPLETE!")
        print("\n✨ Production-Ready Features Implemented:")
        print("\n  1️⃣  Security Sandboxing")
        print("      • Resource limits (CPU, memory, timeout)")
        print("      • Security pattern detection")
        print("      • Subprocess isolation")
        print("      • Optional Docker support")
        print("\n  2️⃣  Cost Management")
        print("      • Token-accurate cost calculation")
        print("      • Daily and monthly budgets")
        print("      • Budget enforcement with exceptions")
        print("      • Per-stage cost breakdown")
        print("      • Multi-model pricing support")
        print("\n  3️⃣  Config Validation")
        print("      • Fail-fast startup validation")
        print("      • LLM provider checks")
        print("      • API key validation")
        print("      • File path verification")
        print("      • Resource limit validation")
        print("\n🚀 Artemis is now production-ready with security and cost controls!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
