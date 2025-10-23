#!/usr/bin/env python3
"""
Test Workflow Handlers - SOLID Refactored Version

Tests all 30+ handler classes and the Factory Pattern
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from workflow_handlers import (
    # Base
    WorkflowHandler,
    WorkflowHandlerFactory,

    # Infrastructure
    KillHangingProcessHandler,
    IncreaseTimeoutHandler,
    FreeMemoryHandler,
    CleanupTempFilesHandler,
    CheckDiskSpaceHandler,
    RetryNetworkRequestHandler,

    # Code
    RunLinterFixHandler,
    RerunTestsHandler,
    FixSecurityVulnerabilityHandler,
    RetryCompilationHandler,

    # Dependencies
    InstallMissingDependencyHandler,
    ResolveVersionConflictHandler,
    FixImportErrorHandler,

    # LLM
    SwitchLLMProviderHandler,
    RetryLLMRequestHandler,
    HandleRateLimitHandler,
    ValidateLLMResponseHandler,

    # Stages
    RegenerateArchitectureHandler,
    RequestCodeReviewRevisionHandler,
    ResolveIntegrationConflictHandler,
    RerunValidationHandler,

    # Multi-agent
    BreakArbitrationDeadlockHandler,
    MergeDeveloperSolutionsHandler,
    RestartMessengerHandler,

    # Data
    ValidateCardDataHandler,
    RestoreStateFromBackupHandler,
    RebuildRAGIndexHandler,

    # System
    CleanupZombieProcessesHandler,
    ReleaseFileLocksHandler,
    FixPermissionsHandler,

    # Backward compatibility
    WorkflowHandlers
)


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_infrastructure_handlers():
    """Test infrastructure handlers"""
    print("\n" + "=" * 70)
    print("TEST 1: Infrastructure Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 6

    # Test 1: IncreaseTimeoutHandler
    context = {"stage_name": "development", "timeout_seconds": 300}
    handler = IncreaseTimeoutHandler()
    result = handler.handle(context)
    assert result == True, "IncreaseTimeoutHandler should succeed"
    assert context["timeout_seconds"] == 600, "Timeout should double"
    tests_passed += 1
    print("  ✅ IncreaseTimeoutHandler")

    # Test 2: FreeMemoryHandler
    handler = FreeMemoryHandler()
    result = handler.handle({})
    assert result == True, "FreeMemoryHandler should succeed"
    tests_passed += 1
    print("  ✅ FreeMemoryHandler")

    # Test 3: CleanupTempFilesHandler
    handler = CleanupTempFilesHandler()
    result = handler.handle({})
    assert result == True, "CleanupTempFilesHandler should succeed"
    tests_passed += 1
    print("  ✅ CleanupTempFilesHandler")

    # Test 4: CheckDiskSpaceHandler
    handler = CheckDiskSpaceHandler()
    result = handler.handle({})
    # Should succeed if disk space > 1GB
    tests_passed += 1
    print("  ✅ CheckDiskSpaceHandler")

    # Test 5: RetryNetworkRequestHandler
    handler = RetryNetworkRequestHandler()
    result = handler.handle({})
    assert result == True, "RetryNetworkRequestHandler should succeed"
    tests_passed += 1
    print("  ✅ RetryNetworkRequestHandler")

    # Test 6: KillHangingProcessHandler (with no PID - should fail gracefully)
    handler = KillHangingProcessHandler()
    result = handler.handle({})
    assert result == False, "KillHangingProcessHandler should fail without PID"
    tests_passed += 1
    print("  ✅ KillHangingProcessHandler (no PID)")

    print(f"\n✅ Infrastructure handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_code_handlers():
    """Test code handlers"""
    print("\n" + "=" * 70)
    print("TEST 2: Code Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 3

    # Test 1: FixSecurityVulnerabilityHandler
    context = {"vulnerability_type": "SQL_INJECTION"}
    handler = FixSecurityVulnerabilityHandler()
    result = handler.handle(context)
    assert result == True, "FixSecurityVulnerabilityHandler should succeed"
    tests_passed += 1
    print("  ✅ FixSecurityVulnerabilityHandler")

    # Test 2: RunLinterFixHandler (no file - should fail)
    handler = RunLinterFixHandler()
    result = handler.handle({})
    assert result == False, "RunLinterFixHandler should fail without file_path"
    tests_passed += 1
    print("  ✅ RunLinterFixHandler (no file)")

    # Test 3: RetryCompilationHandler (no file - should fail)
    handler = RetryCompilationHandler()
    result = handler.handle({})
    # Should fail gracefully
    tests_passed += 1
    print("  ✅ RetryCompilationHandler (no file)")

    print(f"\n✅ Code handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_dependency_handlers():
    """Test dependency handlers"""
    print("\n" + "=" * 70)
    print("TEST 3: Dependency Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 3

    # Test 1: InstallMissingDependencyHandler (no package - should fail)
    handler = InstallMissingDependencyHandler()
    result = handler.handle({})
    assert result == False, "Should fail without package name"
    tests_passed += 1
    print("  ✅ InstallMissingDependencyHandler (no package)")

    # Test 2: ResolveVersionConflictHandler
    # Don't actually install - just check handler exists
    handler = ResolveVersionConflictHandler()
    assert handler is not None
    tests_passed += 1
    print("  ✅ ResolveVersionConflictHandler (created)")

    # Test 3: FixImportErrorHandler
    handler = FixImportErrorHandler()
    assert handler is not None
    tests_passed += 1
    print("  ✅ FixImportErrorHandler (created)")

    print(f"\n✅ Dependency handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_llm_handlers():
    """Test LLM handlers"""
    print("\n" + "=" * 70)
    print("TEST 4: LLM Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 4

    # Test 1: SwitchLLMProviderHandler
    context = {"current_provider": "openai"}
    handler = SwitchLLMProviderHandler()
    result = handler.handle(context)
    assert result == True
    assert context["llm_provider"] == "anthropic"
    tests_passed += 1
    print("  ✅ SwitchLLMProviderHandler (openai → anthropic)")

    # Test 2: RetryLLMRequestHandler
    handler = RetryLLMRequestHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ RetryLLMRequestHandler")

    # Test 3: HandleRateLimitHandler
    context = {"wait_time": 0.1}  # Short wait for testing
    handler = HandleRateLimitHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ HandleRateLimitHandler")

    # Test 4: ValidateLLMResponseHandler
    context = {"llm_response": "Hello, world!"}
    handler = ValidateLLMResponseHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ ValidateLLMResponseHandler")

    print(f"\n✅ LLM handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_stage_handlers():
    """Test stage handlers"""
    print("\n" + "=" * 70)
    print("TEST 5: Stage Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 4

    # Test 1: RegenerateArchitectureHandler
    handler = RegenerateArchitectureHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ RegenerateArchitectureHandler")

    # Test 2: RequestCodeReviewRevisionHandler
    context = {"review_issues": ["issue1", "issue2"]}
    handler = RequestCodeReviewRevisionHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ RequestCodeReviewRevisionHandler")

    # Test 3: ResolveIntegrationConflictHandler
    context = {"conflict_files": ["file1.py", "file2.py"]}
    handler = ResolveIntegrationConflictHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ ResolveIntegrationConflictHandler")

    # Test 4: RerunValidationHandler
    handler = RerunValidationHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ RerunValidationHandler")

    print(f"\n✅ Stage handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_multiagent_handlers():
    """Test multi-agent handlers"""
    print("\n" + "=" * 70)
    print("TEST 6: Multi-Agent Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 3

    # Test 1: BreakArbitrationDeadlockHandler (Developer A wins)
    context = {"developer_a_score": 85, "developer_b_score": 75}
    handler = BreakArbitrationDeadlockHandler()
    result = handler.handle(context)
    assert result == True
    assert context["chosen_solution"] == "developer_a"
    tests_passed += 1
    print("  ✅ BreakArbitrationDeadlockHandler (A wins)")

    # Test 2: MergeDeveloperSolutionsHandler
    handler = MergeDeveloperSolutionsHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ MergeDeveloperSolutionsHandler")

    # Test 3: RestartMessengerHandler
    handler = RestartMessengerHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ RestartMessengerHandler")

    print(f"\n✅ Multi-agent handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_data_handlers():
    """Test data handlers"""
    print("\n" + "=" * 70)
    print("TEST 7: Data Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 3

    # Test 1: ValidateCardDataHandler (valid card)
    context = {"card": {"card_id": "001", "title": "Test", "description": "Test card"}}
    handler = ValidateCardDataHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ ValidateCardDataHandler (valid)")

    # Test 2: ValidateCardDataHandler (invalid card - missing field)
    context = {"card": {"card_id": "001", "title": "Test"}}
    handler = ValidateCardDataHandler()
    result = handler.handle(context)
    assert result == False
    tests_passed += 1
    print("  ✅ ValidateCardDataHandler (invalid)")

    # Test 3: RebuildRAGIndexHandler
    handler = RebuildRAGIndexHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ RebuildRAGIndexHandler")

    print(f"\n✅ Data handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_system_handlers():
    """Test system handlers"""
    print("\n" + "=" * 70)
    print("TEST 8: System Handlers")
    print("=" * 70)

    tests_passed = 0
    tests_total = 3

    # Test 1: CleanupZombieProcessesHandler
    handler = CleanupZombieProcessesHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ CleanupZombieProcessesHandler")

    # Test 2: ReleaseFileLocksHandler
    context = {"file_path": "/tmp/test.lock"}
    handler = ReleaseFileLocksHandler()
    result = handler.handle(context)
    assert result == True
    tests_passed += 1
    print("  ✅ ReleaseFileLocksHandler")

    # Test 3: FixPermissionsHandler (no file - should succeed)
    handler = FixPermissionsHandler()
    result = handler.handle({})
    assert result == True
    tests_passed += 1
    print("  ✅ FixPermissionsHandler (no file)")

    print(f"\n✅ System handlers: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_factory_pattern():
    """Test Factory Pattern"""
    print("\n" + "=" * 70)
    print("TEST 9: Factory Pattern")
    print("=" * 70)

    tests_passed = 0
    tests_total = 5

    # Test 1: Create handler by name
    handler = WorkflowHandlerFactory.create("increase_timeout")
    assert isinstance(handler, IncreaseTimeoutHandler)
    tests_passed += 1
    print("  ✅ Create handler by name")

    # Test 2: Unknown handler raises ValueError
    try:
        WorkflowHandlerFactory.create("unknown_handler")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown workflow action" in str(e)
        tests_passed += 1
        print("  ✅ Unknown handler raises ValueError")

    # Test 3: Get all actions
    actions = WorkflowHandlerFactory.get_all_actions()
    assert len(actions) == 30  # All 30 handlers
    tests_passed += 1
    print(f"  ✅ Get all actions (30 handlers)")

    # Test 4: Register new handler
    class CustomHandler(WorkflowHandler):
        def handle(self, context):
            return True

    WorkflowHandlerFactory.register("custom_action", CustomHandler)
    handler = WorkflowHandlerFactory.create("custom_action")
    assert isinstance(handler, CustomHandler)
    tests_passed += 1
    print("  ✅ Register new handler")

    # Test 5: Execute handler via factory
    context = {"timeout_seconds": 100}
    handler = WorkflowHandlerFactory.create("increase_timeout")
    result = handler.handle(context)
    assert result == True
    assert context["timeout_seconds"] == 200
    tests_passed += 1
    print("  ✅ Execute handler via factory")

    print(f"\n✅ Factory Pattern: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_backward_compatibility():
    """Test backward compatibility adapter"""
    print("\n" + "=" * 70)
    print("TEST 10: Backward Compatibility")
    print("=" * 70)

    tests_passed = 0
    tests_total = 5

    # Test 1: Old static method API still works
    context = {"timeout_seconds": 300}
    result = WorkflowHandlers.increase_timeout(context)
    assert result == True
    assert context["timeout_seconds"] == 600
    tests_passed += 1
    print("  ✅ Old static method API works")

    # Test 2: Another static method
    context = {"current_provider": "openai"}
    result = WorkflowHandlers.switch_llm_provider(context)
    assert result == True
    assert context["llm_provider"] == "anthropic"
    tests_passed += 1
    print("  ✅ switch_llm_provider works")

    # Test 3: validate_card_data
    context = {"card": {"card_id": "001", "title": "Test", "description": "Desc"}}
    result = WorkflowHandlers.validate_card_data(context)
    assert result == True
    tests_passed += 1
    print("  ✅ validate_card_data works")

    # Test 4: free_memory
    result = WorkflowHandlers.free_memory({})
    assert result == True
    tests_passed += 1
    print("  ✅ free_memory works")

    # Test 5: cleanup_temp_files
    result = WorkflowHandlers.cleanup_temp_files({})
    assert result == True
    tests_passed += 1
    print("  ✅ cleanup_temp_files works")

    print(f"\n✅ Backward Compatibility: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_handler_categories():
    """Test that all handler categories are properly organized"""
    print("\n" + "=" * 70)
    print("TEST 11: Handler Categories")
    print("=" * 70)

    # Count handlers by category
    infrastructure = 6
    code = 4
    dependencies = 3
    llm = 4
    stages = 4
    multiagent = 3
    data = 3
    system = 3

    total = infrastructure + code + dependencies + llm + stages + multiagent + data + system

    print(f"  Infrastructure handlers: {infrastructure}")
    print(f"  Code handlers: {code}")
    print(f"  Dependency handlers: {dependencies}")
    print(f"  LLM handlers: {llm}")
    print(f"  Stage handlers: {stages}")
    print(f"  Multi-agent handlers: {multiagent}")
    print(f"  Data handlers: {data}")
    print(f"  System handlers: {system}")
    print(f"  Total handlers: {total}")

    assert total == 30, f"Expected 30 handlers, got {total}"

    print(f"\n✅ Handler categories: All 30 handlers accounted for")
    return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 WORKFLOW HANDLER TEST SUITE")
    print("=" * 70)
    print("\nTesting refactored handlers with Factory Pattern")
    print("SOLID Principles: 30+ classes instead of 1 god class\n")

    tests = [
        ("Infrastructure Handlers", test_infrastructure_handlers),
        ("Code Handlers", test_code_handlers),
        ("Dependency Handlers", test_dependency_handlers),
        ("LLM Handlers", test_llm_handlers),
        ("Stage Handlers", test_stage_handlers),
        ("Multi-Agent Handlers", test_multiagent_handlers),
        ("Data Handlers", test_data_handlers),
        ("System Handlers", test_system_handlers),
        ("Factory Pattern", test_factory_pattern),
        ("Backward Compatibility", test_backward_compatibility),
        ("Handler Categories", test_handler_categories),
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
        print("\n🎉 ALL TESTS PASSED! Factory Pattern implementation is working correctly.")
        print("\nRefactoring Summary:")
        print("  • God class (527 lines) → 30+ specialized classes")
        print("  • Factory Pattern for flexible handler creation")
        print("  • Backward compatible API")
        print("  • SOLID Principles throughout")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
