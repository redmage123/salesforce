#!/usr/bin/env python3
"""
Repository Cleanup Script

Automatically cleans up temporary files, cache directories,
and other unwanted artifacts from the repository.
"""

import os
import shutil
import glob
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class RepositoryCleanup:
    """Handle repository cleanup operations"""

    # Patterns to always delete
    DELETE_PATTERNS = [
        '**/*.pyc',
        '**/__pycache__',
        '**/.ipynb_checkpoints',
        '**/.pytest_cache',
        '**/.mypy_cache',
        '**/*.egg-info',
        '**/.DS_Store',
        '**/Thumbs.db',
        '**/*.tmp',
        '**/*.bak',
        '**/*.swp',
        '**/*~',
    ]

    # Patterns to review before deleting
    REVIEW_PATTERNS = [
        '**/*_backup.*',
        '**/*_old.*',
        '**/*_executed.ipynb',
    ]

    # Patterns to never delete
    PRESERVE_PATTERNS = [
        '.git/**',
        '.gitignore',
        '.gitattributes',
        'LICENSE',
        'README.md',
        '**/*.md',
        'requirements.txt',
        'package.json',
        'pyproject.toml',
    ]

    def __init__(self, repo_path: str = '.', verbose: bool = True):
        self.repo_path = Path(repo_path)
        self.verbose = verbose
        self.cleanup_report = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'cleanup_type': 'automatic',
            'files_deleted': [],
            'directories_removed': [],
            'total_deleted': 0,
            'space_freed_bytes': 0,
            'space_freed_mb': 0.0,
            'warnings': [],
            'errors': []
        }

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(message)

    def is_preserved(self, path: Path) -> bool:
        """Check if path matches preserve patterns"""
        path_str = str(path)
        for pattern in self.PRESERVE_PATTERNS:
            if path.match(pattern):
                return True
        return False

    def is_git_tracked(self, path: Path) -> bool:
        """Check if file is tracked by git"""
        import subprocess
        result = subprocess.run(
            ['git', 'ls-files', '--error-unmatch', str(path)],
            capture_output=True,
            cwd=self.repo_path
        )
        return result.returncode == 0

    def get_size(self, path: Path) -> int:
        """Get size of file or directory"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
            return total_size
        return 0

    def delete_file(self, path: Path) -> bool:
        """Safely delete a file"""
        try:
            # Get size before deletion
            size = self.get_size(path)

            if path.is_file():
                path.unlink()
                self.log(f"  Deleted file: {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                self.cleanup_report['directories_removed'].append(str(path))
                self.log(f"  Deleted directory: {path}")

            self.cleanup_report['files_deleted'].append(str(path))
            self.cleanup_report['space_freed_bytes'] += size
            self.cleanup_report['total_deleted'] += 1
            return True

        except Exception as e:
            self.cleanup_report['errors'].append({
                'file': str(path),
                'error': str(e)
            })
            self.log(f"  ❌ Error deleting {path}: {e}")
            return False

    def cleanup_by_pattern(self, patterns: List[str]) -> int:
        """Clean up files matching patterns"""
        deleted_count = 0

        for pattern in patterns:
            matches = list(self.repo_path.glob(pattern))

            for path in matches:
                # Skip if preserved
                if self.is_preserved(path):
                    self.log(f"  🔒 Preserving: {path}")
                    continue

                # Skip if git tracked (should use git rm)
                if self.is_git_tracked(path):
                    self.cleanup_report['warnings'].append({
                        'file': str(path),
                        'warning': 'File is tracked by git, skipping'
                    })
                    self.log(f"  ⚠️  Tracked by git: {path}")
                    continue

                # Delete
                if self.delete_file(path):
                    deleted_count += 1

        return deleted_count

    def remove_empty_directories(self) -> int:
        """Remove empty directories"""
        removed_count = 0

        for root, dirs, files in os.walk(self.repo_path, topdown=False):
            for dirname in dirs:
                dirpath = Path(root) / dirname

                # Skip .git directory
                if '.git' in dirpath.parts:
                    continue

                # Check if empty
                try:
                    if not any(dirpath.iterdir()):
                        dirpath.rmdir()
                        self.cleanup_report['directories_removed'].append(str(dirpath))
                        self.log(f"  Removed empty directory: {dirpath}")
                        removed_count += 1
                except Exception as e:
                    self.cleanup_report['errors'].append({
                        'directory': str(dirpath),
                        'error': str(e)
                    })

        return removed_count

    def run_cleanup(self, include_review: bool = False) -> Dict:
        """Run full cleanup"""
        self.log("🧹 Starting repository cleanup...")

        # 1. Clean up automatic delete patterns
        self.log("\n📋 Cleaning automatic delete patterns...")
        deleted = self.cleanup_by_pattern(self.DELETE_PATTERNS)
        self.log(f"✅ Deleted {deleted} items")

        # 2. Review patterns (if enabled)
        if include_review:
            self.log("\n📋 Cleaning review patterns...")
            deleted = self.cleanup_by_pattern(self.REVIEW_PATTERNS)
            self.log(f"✅ Deleted {deleted} items from review")

        # 3. Remove empty directories
        self.log("\n📋 Removing empty directories...")
        removed = self.remove_empty_directories()
        self.log(f"✅ Removed {removed} empty directories")

        # Calculate totals
        self.cleanup_report['space_freed_mb'] = round(
            self.cleanup_report['space_freed_bytes'] / (1024 * 1024),
            2
        )

        # Print summary
        self.log("\n" + "=" * 60)
        self.log("📊 CLEANUP SUMMARY")
        self.log("=" * 60)
        self.log(f"Total items deleted: {self.cleanup_report['total_deleted']}")
        self.log(f"Directories removed: {len(self.cleanup_report['directories_removed'])}")
        self.log(f"Space freed: {self.cleanup_report['space_freed_mb']} MB")
        if self.cleanup_report['warnings']:
            self.log(f"Warnings: {len(self.cleanup_report['warnings'])}")
        if self.cleanup_report['errors']:
            self.log(f"Errors: {len(self.cleanup_report['errors'])}")
        self.log("=" * 60)

        return self.cleanup_report

    def save_report(self, output_file: str = None):
        """Save cleanup report to JSON"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"/tmp/repo_cleanup_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(self.cleanup_report, f, indent=2)

        self.log(f"\n📄 Report saved: {output_file}")
        return output_file


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Clean up repository temporary files and artifacts'
    )
    parser.add_argument(
        '--path',
        default='.',
        help='Repository path (default: current directory)'
    )
    parser.add_argument(
        '--include-review',
        action='store_true',
        help='Include review patterns in cleanup'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output'
    )
    parser.add_argument(
        '--report',
        help='Output file for cleanup report'
    )

    args = parser.parse_args()

    # Run cleanup
    cleaner = RepositoryCleanup(
        repo_path=args.path,
        verbose=not args.quiet
    )

    report = cleaner.run_cleanup(include_review=args.include_review)

    # Save report
    if args.report or not args.quiet:
        cleaner.save_report(args.report)

    # Exit with error code if there were errors
    if report['errors']:
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
