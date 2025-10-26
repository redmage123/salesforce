#!/usr/bin/env python3
"""
Git Operations Manager

Manages git operations including branches, commits, pushes, pulls,
and remote repository synchronization.
"""

import os
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from debug_mixin import DebugMixin


class GitManager(DebugMixin):
    """Manage git operations"""

    def __init__(self, repo_path: str = '.', verbose: bool = True):
        DebugMixin.__init__(self, component_name="git")
        self.repo_path = Path(repo_path)
        self.verbose = verbose
        self.operations_log = {
            'operations': [],
            'summary': {
                'total_operations': 0,
                'successful': 0,
                'failed': 0
            }
        }

        # Load config
        config_file = Path(__file__).parent / 'repo_cleanup_config.json'
        if config_file.exists():
            with open(config_file) as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(message)

    def run_git_command(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run git command"""
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            cwd=self.repo_path,
            check=False
        )

        if check and result.returncode != 0:
            error_msg = result.stderr.decode().strip()
            self.log(f"❌ Git command failed: {' '.join(args)}")
            self.log(f"   Error: {error_msg}")

        return result

    def log_operation(self, op_type: str, details: Dict, status: str = 'success'):
        """Log git operation"""
        operation = {
            'type': op_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': status,
            **details
        }

        self.operations_log['operations'].append(operation)
        self.operations_log['summary']['total_operations'] += 1

        if status == 'success':
            self.operations_log['summary']['successful'] += 1
        else:
            self.operations_log['summary']['failed'] += 1

    def get_current_branch(self) -> str:
        """Get current branch name"""
        result = self.run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
        return result.stdout.decode().strip()

    def get_status(self) -> Dict:
        """Get repository status"""
        current_branch = self.get_current_branch()

        # Uncommitted changes
        result = self.run_git_command(['status', '--porcelain'])
        uncommitted_lines = result.stdout.decode().strip().split('\n')
        uncommitted = len([l for l in uncommitted_lines if l])

        # Unpushed commits
        result = self.run_git_command(
            ['log', f'origin/{current_branch}..{current_branch}', '--oneline'],
            check=False
        )
        unpushed_lines = result.stdout.decode().strip().split('\n')
        unpushed = len([l for l in unpushed_lines if l])

        # Unpulled commits
        self.run_git_command(['fetch', 'origin'], check=False)
        result = self.run_git_command(
            ['log', f'{current_branch}..origin/{current_branch}', '--oneline'],
            check=False
        )
        unpulled_lines = result.stdout.decode().strip().split('\n')
        unpulled = len([l for l in unpulled_lines if l])

        return {
            'branch': current_branch,
            'uncommitted_changes': uncommitted,
            'unpushed_commits': unpushed,
            'unpulled_commits': unpulled
        }

    def create_branch(self, branch_name: str, from_branch: str = 'main') -> bool:
        """Create new branch"""
        self.debug_log("Creating branch", branch_name=branch_name, from_branch=from_branch)
        self.log(f"📋 Creating branch: {branch_name}")

        # Checkout base branch
        result = self.run_git_command(['checkout', from_branch])
        if result.returncode != 0:
            self.debug_log("Branch creation failed - checkout failed", branch=branch_name, from_branch=from_branch)
            self.log_operation('branch_create', {'branch': branch_name}, 'failed')
            return False

        # Pull latest
        result = self.run_git_command(['pull', 'origin', from_branch])
        if result.returncode != 0:
            self.log(f"⚠️  Pull failed, continuing anyway")

        # Create new branch
        result = self.run_git_command(['checkout', '-b', branch_name])
        if result.returncode != 0:
            self.log_operation('branch_create', {'branch': branch_name}, 'failed')
            return False

        self.log(f"✅ Created branch: {branch_name}")
        self.log_operation('branch_create', {
            'branch': branch_name,
            'from_branch': from_branch
        })
        return True

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to branch"""
        self.log(f"📋 Switching to branch: {branch_name}")

        result = self.run_git_command(['checkout', branch_name])
        if result.returncode != 0:
            self.log_operation('branch_switch', {'branch': branch_name}, 'failed')
            return False

        self.log(f"✅ Switched to: {branch_name}")
        self.log_operation('branch_switch', {'branch': branch_name})
        return True

    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        """Delete local branch"""
        self.log(f"📋 Deleting branch: {branch_name}")

        flag = '-D' if force else '-d'
        result = self.run_git_command(['branch', flag, branch_name])
        if result.returncode != 0:
            self.log_operation('branch_delete', {
                'branch': branch_name,
                'force': force
            }, 'failed')
            return False

        self.log(f"✅ Deleted branch: {branch_name}")
        self.log_operation('branch_delete', {
            'branch': branch_name,
            'force': force
        })
        return True

    def commit(self, message: str, files: List[str] = None) -> bool:
        """Create commit"""
        self.debug_log("Creating commit", message=message[:50], files_count=len(files) if files else "all")
        self.log(f"📋 Creating commit: {message[:50]}...")

        # Stage files
        if files:
            # Stage individual files, log failures
            [self.log(f"⚠️  Failed to stage: {file}")
             for file in files
             if self.run_git_command(['add', file]).returncode != 0]
        else:
            # Stage all changes
            self.run_git_command(['add', '.'])

        # Create commit
        result = self.run_git_command(['commit', '-m', message])
        if result.returncode != 0:
            self.log_operation('commit', {'message': message}, 'failed')
            return False

        # Get commit hash
        result = self.run_git_command(['rev-parse', 'HEAD'])
        commit_hash = result.stdout.decode().strip()[:7]

        self.log(f"✅ Created commit: {commit_hash}")
        self.log_operation('commit', {
            'message': message,
            'commit_hash': commit_hash,
            'files_count': len(files) if files else 'all'
        })
        return True

    def push(self, branch: str = None, force: bool = False) -> bool:
        """Push to remote"""
        if not branch:
            branch = self.get_current_branch()

        self.debug_log("Pushing to remote", branch=branch, force=force)
        self.log(f"📋 Pushing to: {branch}")

        # Check if protected branch
        protected = self.config.get('git_operations', {}).get('protected_branches', [])
        if branch in protected and force:
            self.debug_log("Force push blocked - protected branch", branch=branch)
            self.log(f"❌ Cannot force push to protected branch: {branch}")
            return False

        # Auto pull if configured
        if self.config.get('git_operations', {}).get('auto_pull_before_push', True):
            self.log("  Pulling latest changes first...")
            self.run_git_command(['pull', 'origin', branch, '--rebase'], check=False)

        # Push
        args = ['push', 'origin', branch]
        if force:
            args.append('--force')

        result = self.run_git_command(args)
        if result.returncode != 0:
            self.log_operation('push', {
                'branch': branch,
                'force': force
            }, 'failed')
            return False

        self.log(f"✅ Pushed to: {branch}")
        self.log_operation('push', {
            'branch': branch,
            'force': force
        })
        return True

    def pull(self, branch: str = None, rebase: bool = True) -> bool:
        """Pull from remote"""
        if not branch:
            branch = self.get_current_branch()

        self.log(f"📋 Pulling from: {branch}")

        args = ['pull', 'origin', branch]
        if rebase:
            args.append('--rebase')

        result = self.run_git_command(args)
        if result.returncode != 0:
            self.log_operation('pull', {
                'branch': branch,
                'rebase': rebase
            }, 'failed')
            return False

        self.log(f"✅ Pulled from: {branch}")
        self.log_operation('pull', {
            'branch': branch,
            'rebase': rebase
        })
        return True

    def cleanup_merged_branches(self, remote: bool = False) -> List[str]:
        """Delete merged branches"""
        self.log("📋 Cleaning up merged branches...")

        # Get merged branches
        result = self.run_git_command(['branch', '--merged', 'main'])
        branches = result.stdout.decode().strip().split('\n')

        # Filter and process branches using list comprehension
        protected_branches = {'main', 'master', ''}
        processable_branches = [
            branch.strip().replace('* ', '')
            for branch in branches
            if branch.strip().replace('* ', '') not in protected_branches
        ]

        # Delete branches
        deleted = [branch for branch in processable_branches if self.delete_branch(branch)]

        # Delete remote branches if requested
        if remote:
            [self.run_git_command(['push', 'origin', '--delete', branch], check=False)
             for branch in deleted]

        self.log(f"✅ Deleted {len(deleted)} merged branches")
        return deleted

    def save_operations_log(self, card_id: str = None, output_file: str = None):
        """Save operations log"""
        if not output_file:
            # Get git operations directory from env or use default
            git_ops_dir = os.getenv("ARTEMIS_GIT_OPS_DIR", "../../.artemis_data/git_operations")
            if not os.path.isabs(git_ops_dir):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                git_ops_dir = os.path.join(script_dir, git_ops_dir)

            # Ensure directory exists
            os.makedirs(git_ops_dir, exist_ok=True)

            if card_id:
                output_file = os.path.join(git_ops_dir, f"git_operations_{card_id}.json")
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = os.path.join(git_ops_dir, f"git_operations_{timestamp}.json")

        with open(output_file, 'w') as f:
            json.dump(self.operations_log, f, indent=2)

        self.log(f"\n📄 Operations log saved: {output_file}")
        return output_file


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Manage git operations'
    )
    parser.add_argument('--path', default='.', help='Repository path')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--create-branch', help='Create new branch')
    parser.add_argument('--delete-branch', help='Delete branch')
    parser.add_argument('--commit', help='Commit message')
    parser.add_argument('--push', action='store_true', help='Push to remote')
    parser.add_argument('--pull', action='store_true', help='Pull from remote')
    parser.add_argument('--cleanup-merged', action='store_true', help='Cleanup merged branches')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    manager = GitManager(repo_path=args.path, verbose=not args.quiet)

    if args.status:
        status = manager.get_status()
        print(json.dumps(status, indent=2))

    if args.create_branch:
        manager.create_branch(args.create_branch)

    if args.delete_branch:
        manager.delete_branch(args.delete_branch)

    if args.commit:
        manager.commit(args.commit)

    if args.pull:
        manager.pull()

    if args.push:
        manager.push()

    if args.cleanup_merged:
        manager.cleanup_merged_branches(remote=True)

    return 0


if __name__ == '__main__':
    exit(main())
