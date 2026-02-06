#!/usr/bin/env python3
"""
Data Protection Module for Status Tracker

This module provides functionality to protect SQLite database files
during git operations, cleanup, and re-initialization.

Features:
- Backup data files before risky operations
- Restore data files if accidentally removed
- Prevent accidental deletion during git clean/reset
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Configuration
DATA_DIR = Path("/home/node/.openclaw/workspace/status-tracker/data")
BACKUP_DIR = Path("/home/node/.openclaw/workspace/status-tracker/.data_backups")
PROTECTION_MANIFEST = BACKUP_DIR / "protection_manifest.json"
PROTECTED_PATTERNS = ["*.db", "*.sqlite", "*.sqlite3"]


def ensure_directories():
    """Ensure data and backup directories exist."""
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)


def get_protected_files() -> List[Path]:
    """Get list of all protected database files in data directory."""
    protected = []
    if DATA_DIR.exists():
        for pattern in PROTECTED_PATTERNS:
            protected.extend(DATA_DIR.glob(pattern))
    return protected


def create_backup(suffix: Optional[str] = None) -> dict:
    """
    Create a backup of all protected data files.

    Args:
        suffix: Optional suffix for the backup (e.g., 'pre-clean', 'pre-reset')

    Returns:
        dict: Backup metadata including timestamp and backed up files
    """
    ensure_directories()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if suffix:
        backup_name = f"backup_{timestamp}_{suffix}"
    else:
        backup_name = f"backup_{timestamp}"

    backup_path = BACKUP_DIR / backup_name
    backup_path.mkdir(exist_ok=True)

    protected_files = get_protected_files()
    backed_up = []

    for file_path in protected_files:
        if file_path.exists():
            dest = backup_path / file_path.name
            shutil.copy2(file_path, dest)
            backed_up.append(str(file_path.name))

    # Update manifest
    manifest = load_manifest()
    backup_entry = {
        "timestamp": timestamp,
        "suffix": suffix,
        "path": str(backup_path),
        "files": backed_up,
        "created_at": datetime.now().isoformat(),
    }
    manifest["backups"].append(backup_entry)
    save_manifest(manifest)

    print(f"✓ Created backup: {backup_name}")
    print(f"  Files backed up: {len(backed_up)}")
    for f in backed_up:
        print(f"    - {f}")

    return backup_entry


def load_manifest() -> dict:
    """Load the protection manifest."""
    if PROTECTION_MANIFEST.exists():
        with open(PROTECTION_MANIFEST, "r") as f:
            return json.load(f)
    return {"backups": [], "protected_patterns": PROTECTED_PATTERNS}


def save_manifest(manifest: dict):
    """Save the protection manifest."""
    with open(PROTECTION_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


def restore_latest() -> bool:
    """
    Restore data files from the latest backup.

    Returns:
        bool: True if restoration was successful
    """
    manifest = load_manifest()

    if not manifest["backups"]:
        print("✗ No backups found")
        return False

    latest_backup = manifest["backups"][-1]
    backup_path = Path(latest_backup["path"])

    if not backup_path.exists():
        print(f"✗ Backup path not found: {backup_path}")
        return False

    ensure_directories()
    restored = []

    for file_name in latest_backup["files"]:
        src = backup_path / file_name
        dest = DATA_DIR / file_name
        if src.exists():
            shutil.copy2(src, dest)
            restored.append(file_name)

    print(f"✓ Restored from backup: {latest_backup.get('suffix', 'latest')}")
    print(f"  Files restored: {len(restored)}")
    for f in restored:
        print(f"    - {f}")

    return len(restored) > 0


def list_backups():
    """List all available backups."""
    manifest = load_manifest()

    if not manifest["backups"]:
        print("No backups found")
        return

    print("\nAvailable Backups:")
    print("-" * 80)
    for i, backup in enumerate(manifest["backups"], 1):
        suffix = backup.get("suffix", "N/A")
        timestamp = backup["timestamp"]
        file_count = len(backup["files"])
        print(f"{i}. {timestamp} ({suffix}) - {file_count} files")
        for f in backup["files"]:
            print(f"      - {f}")
    print("-" * 80)


def check_data_integrity() -> bool:
    """
    Check if data files exist and are valid.

    Returns:
        bool: True if all data files are present
    """
    protected_files = get_protected_files()

    if not protected_files:
        print("⚠ No database files found in data/ directory")
        return False

    all_valid = True
    print("\nData Integrity Check:")
    for file_path in protected_files:
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ✓ {file_path.name} ({size} bytes)")
        else:
            print(f"  ✗ {file_path.name} - MISSING")
            all_valid = False

    return all_valid


def protect_for_git_operation(operation: str):
    """
    Protect data files before a git operation.

    Args:
        operation: Name of the git operation (e.g., 'clean', 'reset', 'checkout')
    """
    print(f"\n🔒 Protecting data files before git {operation}...")
    create_backup(suffix=f"pre-{operation}")

    # Create a sentinel file to detect if data was removed
    sentinel = BACKUP_DIR / ".data_protection_active"
    with open(sentinel, "w") as f:
        f.write(f"Protection active since: {datetime.now().isoformat()}\n")
        f.write(f"Operation: git {operation}\n")


def verify_protection_after_operation(operation: str) -> bool:
    """
    Verify data files after a git operation and restore if needed.

    Args:
        operation: Name of the git operation

    Returns:
        bool: True if data is intact or was successfully restored
    """
    print(f"\n🔍 Verifying data integrity after git {operation}...")

    protected_files = get_protected_files()
    missing_files = [f for f in protected_files if not f.exists()]

    if missing_files:
        print(
            f"⚠ Warning: {len(missing_files)} data file(s) missing after git {operation}"
        )
        for f in missing_files:
            print(f"    - {f.name}")

        response = input("\nRestore from latest backup? (y/N): ")
        if response.lower() == "y":
            return restore_latest()
        return False
    else:
        print("✓ All data files are intact")
        return True


def cleanup_old_backups(keep_count: int = 10):
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        keep_count: Number of recent backups to keep
    """
    manifest = load_manifest()

    if len(manifest["backups"]) <= keep_count:
        return

    backups_to_remove = manifest["backups"][:-keep_count]

    for backup in backups_to_remove:
        backup_path = Path(backup["path"])
        if backup_path.exists():
            shutil.rmtree(backup_path)
            print(f"✓ Removed old backup: {backup_path.name}")

    manifest["backups"] = manifest["backups"][-keep_count:]
    save_manifest(manifest)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python protect_data.py <command> [options]")
        print("\nCommands:")
        print("  backup [suffix]     - Create a backup of data files")
        print("  restore             - Restore from latest backup")
        print("  list                - List all backups")
        print("  check               - Check data integrity")
        print("  pre-git <operation> - Protect before git operation")
        print("  post-git <operation> - Verify/restore after git operation")
        print("  cleanup [count]     - Remove old backups (keep last N)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "backup":
        suffix = sys.argv[2] if len(sys.argv) > 2 else None
        create_backup(suffix)
    elif command == "restore":
        restore_latest()
    elif command == "list":
        list_backups()
    elif command == "check":
        check_data_integrity()
    elif command == "pre-git":
        if len(sys.argv) < 3:
            print("Error: specify git operation (e.g., 'clean', 'reset')")
            sys.exit(1)
        protect_for_git_operation(sys.argv[2])
    elif command == "post-git":
        if len(sys.argv) < 3:
            print("Error: specify git operation (e.g., 'clean', 'reset')")
            sys.exit(1)
        verify_protection_after_operation(sys.argv[2])
    elif command == "cleanup":
        keep_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cleanup_old_backups(keep_count)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
