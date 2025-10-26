#!/usr/bin/env python3
"""
Artemis CLI - Unified command-line interface for Artemis helper tools

This CLI provides access to all Artemis helper scripts and utilities
as subcommands, eliminating the need to run standalone scripts manually.

Usage:
    artemis init-prompts    # Initialize all prompts with DEPTH framework
    artemis test-config     # Test Hydra configuration and storage
    artemis run [card-id]   # Run Artemis orchestrator on a task
    artemis cleanup         # Clean up temporary files and reset state
    artemis status          # Show Artemis system status
    artemis prompts         # Manage prompt templates
"""

import sys
import os
from pathlib import Path
import argparse
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_init_prompts(args):
    """Initialize all Artemis prompts with DEPTH framework"""
    print("=" * 70)
    print("Initializing Artemis Prompts")
    print("=" * 70)

    try:
        from initialize_artemis_prompts import create_all_artemis_prompts, create_default_prompts
        from prompt_manager import PromptManager
        from rag_agent import RAGAgent
        from hydra import initialize, compose

        # Initialize Hydra to get RAG DB path
        with initialize(version_base=None, config_path="conf"):
            cfg = compose(config_name="config")
            rag_db_path = cfg.storage.rag_db_path

        print(f"\n📁 Using RAG database: {rag_db_path}")

        # Initialize RAG and PromptManager
        rag = RAGAgent(db_path=rag_db_path, verbose=args.verbose)
        pm = PromptManager(rag, verbose=args.verbose)

        # Create default prompts
        print("\n🔧 Creating default prompts...")
        create_default_prompts(pm)

        # Create all other Artemis prompts
        print("\n🔧 Creating Artemis-specific prompts...")
        create_all_artemis_prompts(pm)

        print("\n" + "=" * 70)
        print("✅ PROMPTS INITIALIZED!")
        print("=" * 70)
        print("\nYou can now query prompts from agents:")
        print("  prompt = pm.get_prompt('developer_conservative_implementation')")
        print("  rendered = pm.render_prompt(prompt, variables)")

    except Exception as e:
        print(f"\n❌ Error initializing prompts: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def cmd_test_config(args):
    """Test Hydra configuration and storage setup"""
    print("=" * 70)
    print("Testing Artemis Configuration")
    print("=" * 70)

    try:
        from test_hydra_logging_storage import test_all

        # Run all tests
        success = test_all()

        if success:
            print("\n✅ All configuration tests passed!")
            return 0
        else:
            print("\n❌ Some configuration tests failed")
            return 1

    except Exception as e:
        print(f"\n❌ Error testing configuration: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_run(args):
    """Run Artemis orchestrator on a task"""
    print("=" * 70)
    print(f"Running Artemis on task: {args.card_id}")
    print("=" * 70)

    try:
        import subprocess
        import sys

        # Build command to run artemis_orchestrator.py
        cmd = [
            sys.executable,
            "artemis_orchestrator.py",
            "--card-id", args.card_id
        ]

        if args.full:
            cmd.append("--full")

        if args.resume:
            cmd.append("--resume")

        # Add Hydra overrides
        if args.overrides:
            for override in args.overrides:
                cmd.append(override)

        # Run the command
        print(f"\n🚀 Starting Artemis pipeline...")
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

        if result.returncode == 0:
            print("\n✅ Pipeline completed successfully!")
            return 0
        else:
            print(f"\n❌ Pipeline failed with exit code: {result.returncode}")
            return result.returncode

    except Exception as e:
        print(f"\n❌ Error running pipeline: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_cleanup(args):
    """Clean up Artemis temporary files and reset state"""
    print("=" * 70)
    print("Cleaning up Artemis workspace")
    print("=" * 70)

    try:
        from hydra import initialize, compose
        import shutil

        # Get storage paths from config
        with initialize(version_base=None, config_path="conf"):
            cfg = compose(config_name="config")

            paths_to_clean = {
                "Temporary files": cfg.storage.temp_dir,
                "Checkpoints": cfg.storage.checkpoint_dir if not args.keep_checkpoints else None,
                "State files": cfg.storage.state_dir if args.full_reset else None,
            }

            # Clean up paths
            for description, path in paths_to_clean.items():
                if path is None:
                    continue

                path_obj = Path(path)
                if path_obj.exists():
                    print(f"\n🧹 Cleaning {description}: {path}")
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj)
                        path_obj.mkdir(parents=True, exist_ok=True)
                    else:
                        path_obj.unlink()
                else:
                    print(f"⏭️  Skipping {description} (doesn't exist): {path}")

            print("\n✅ Cleanup complete!")

            if args.full_reset:
                print("\n⚠️  Full reset performed - all state and checkpoints cleared")
            elif args.keep_checkpoints:
                print("\n💾 Checkpoints preserved")

    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def cmd_status(args):
    """Show Artemis system status"""
    print("=" * 70)
    print("Artemis System Status")
    print("=" * 70)

    try:
        from hydra import initialize, compose
        import json

        # Get configuration
        with initialize(version_base=None, config_path="conf"):
            cfg = compose(config_name="config")

            # Check paths
            print("\n📁 Storage Paths:")
            paths = {
                "RAG Database": cfg.storage.rag_db_path,
                "Temp Directory": cfg.storage.temp_dir,
                "Checkpoints": cfg.storage.checkpoint_dir,
                "State": cfg.storage.state_dir,
                "ADRs": cfg.storage.adr_dir,
                "Developer Output": cfg.storage.developer_output_dir,
                "Messages": cfg.storage.message_dir,
            }

            for name, path in paths.items():
                path_obj = Path(path)
                exists = "✅" if path_obj.exists() else "❌"
                print(f"  {exists} {name}: {path}")

            # Check LLM configuration
            print("\n🤖 LLM Configuration:")
            print(f"  Provider: {cfg.llm.provider}")
            print(f"  Model: {cfg.llm.model}")

            # Check kanban board
            print("\n📋 Kanban Board:")
            kanban_path = Path("kanban_board.json")
            if kanban_path.exists():
                with open(kanban_path) as f:
                    board = json.load(f)
                    columns = board.get("columns", {})
                    total_cards = sum(len(cards) for cards in columns.values())
                    print(f"  Total cards: {total_cards}")
                    for col_name, cards in columns.items():
                        print(f"    {col_name}: {len(cards)} cards")
            else:
                print("  ❌ Kanban board not found")

            # Check for checkpoints
            print("\n💾 Recent Checkpoints:")
            checkpoint_dir = Path(cfg.storage.checkpoint_dir)
            if checkpoint_dir.exists():
                checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if checkpoints:
                    for cp in checkpoints[:5]:  # Show last 5
                        print(f"  📝 {cp.name}")
                else:
                    print("  No checkpoints found")
            else:
                print("  ❌ Checkpoint directory doesn't exist")

    except Exception as e:
        print(f"\n❌ Error getting status: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def cmd_prompts(args):
    """Manage prompt templates"""
    print("=" * 70)
    print("Artemis Prompt Manager")
    print("=" * 70)

    try:
        from prompt_manager import PromptManager
        from rag_agent import RAGAgent
        from hydra import initialize, compose
        import json

        # Initialize Hydra to get RAG DB path
        with initialize(version_base=None, config_path="conf"):
            cfg = compose(config_name="config")
            rag_db_path = cfg.storage.rag_db_path

        # Initialize RAG and PromptManager
        rag = RAGAgent(db_path=rag_db_path, verbose=False)
        pm = PromptManager(rag, verbose=False)

        if args.action == "list":
            # List all prompts
            print("\n📝 Available Prompts:\n")
            for category in pm.PROMPT_CATEGORIES:
                prompts = pm.query_prompts(category=category, top_k=10)
                if prompts:
                    print(f"\n{category}:")
                    for p in prompts:
                        print(f"  • {p.name} (v{p.version})")
                        print(f"    Tags: {', '.join(p.tags)}")
                        print(f"    Usage: {p.usage_count} | Score: {p.performance_score:.2f}")

        elif args.action == "show":
            # Show specific prompt
            if not args.name:
                print("❌ Error: --name required for 'show' action")
                return 1

            prompt = pm.get_prompt(args.name)
            if not prompt:
                print(f"❌ Prompt not found: {args.name}")
                return 1

            print(f"\n📝 Prompt: {prompt.name} (v{prompt.version})")
            print(f"Category: {prompt.category}")
            print(f"Tags: {', '.join(prompt.tags)}")
            print(f"\nPerspectives:")
            for p in prompt.perspectives:
                print(f"  • {p}")
            print(f"\nSuccess Metrics:")
            for m in prompt.success_metrics:
                print(f"  • {m}")
            print(f"\nTask Breakdown:")
            for i, t in enumerate(prompt.task_breakdown, 1):
                print(f"  {i}. {t}")

        elif args.action == "search":
            # Search prompts
            if not args.query:
                print("❌ Error: --query required for 'search' action")
                return 1

            results = pm.rag.query_similar(
                query_text=args.query,
                artifact_types=["prompt_template"],
                top_k=5
            )

            print(f"\n🔍 Search results for: '{args.query}'\n")
            for result in results:
                prompt_data = result["metadata"]["prompt_data"]
                if isinstance(prompt_data, str):
                    prompt_data = json.loads(prompt_data)
                print(f"  • {prompt_data['name']} (v{prompt_data['version']})")
                print(f"    Category: {prompt_data['category']}")
                print(f"    Score: {result['score']:.3f}")
                print()

    except Exception as e:
        print(f"\n❌ Error managing prompts: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Artemis CLI - Unified interface for Artemis tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init-prompts command
    parser_init = subparsers.add_parser(
        "init-prompts",
        help="Initialize all prompts with DEPTH framework"
    )
    parser_init.set_defaults(func=cmd_init_prompts)

    # test-config command
    parser_test = subparsers.add_parser(
        "test-config",
        help="Test Hydra configuration and storage"
    )
    parser_test.set_defaults(func=cmd_test_config)

    # run command
    parser_run = subparsers.add_parser(
        "run",
        help="Run Artemis orchestrator on a task"
    )
    parser_run.add_argument(
        "card_id",
        help="Card ID to process"
    )
    parser_run.add_argument(
        "--full",
        action="store_true",
        help="Run full pipeline"
    )
    parser_run.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint"
    )
    parser_run.add_argument(
        "--override",
        dest="overrides",
        action="append",
        help="Hydra config overrides (e.g., llm.model=gpt-4o)"
    )
    parser_run.set_defaults(func=cmd_run)

    # cleanup command
    parser_cleanup = subparsers.add_parser(
        "cleanup",
        help="Clean up temporary files and reset state"
    )
    parser_cleanup.add_argument(
        "--full-reset",
        action="store_true",
        help="Full reset including state files"
    )
    parser_cleanup.add_argument(
        "--keep-checkpoints",
        action="store_true",
        help="Keep checkpoint files"
    )
    parser_cleanup.set_defaults(func=cmd_cleanup)

    # status command
    parser_status = subparsers.add_parser(
        "status",
        help="Show Artemis system status"
    )
    parser_status.set_defaults(func=cmd_status)

    # prompts command
    parser_prompts = subparsers.add_parser(
        "prompts",
        help="Manage prompt templates"
    )
    parser_prompts.add_argument(
        "action",
        choices=["list", "show", "search"],
        help="Action to perform"
    )
    parser_prompts.add_argument(
        "--name",
        help="Prompt name (for 'show' action)"
    )
    parser_prompts.add_argument(
        "--query",
        help="Search query (for 'search' action)"
    )
    parser_prompts.set_defaults(func=cmd_prompts)

    # Parse args
    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0

    # Run command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
