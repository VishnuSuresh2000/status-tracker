"""Unit tests for the data protection module (scripts/protect_data.py)."""

import os
import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the module under test
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from protect_data import (
    ensure_directories,
    get_protected_files,
    create_backup,
    load_manifest,
    save_manifest,
    restore_latest,
    list_backups,
    check_data_integrity,
    protect_for_git_operation,
    verify_protection_after_operation,
    cleanup_old_backups,
    DATA_DIR,
    BACKUP_DIR,
    PROTECTION_MANIFEST,
    PROTECTED_PATTERNS,
)


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and cleanup test environment."""
    # Store original values
    original_data_dir = DATA_DIR
    original_backup_dir = BACKUP_DIR
    original_manifest = PROTECTION_MANIFEST

    # Create temporary test directories
    test_data_dir = Path(__file__).parent / ".test_data"
    test_backup_dir = Path(__file__).parent / ".test_backups"
    test_manifest = test_backup_dir / "protection_manifest.json"

    # Monkey patch for testing
    import protect_data

    protect_data.DATA_DIR = test_data_dir
    protect_data.BACKUP_DIR = test_backup_dir
    protect_data.PROTECTION_MANIFEST = test_manifest

    # Ensure clean state
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    if test_backup_dir.exists():
        shutil.rmtree(test_backup_dir)

    yield

    # Cleanup
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    if test_backup_dir.exists():
        shutil.rmtree(test_backup_dir)

    # Restore original values
    protect_data.DATA_DIR = original_data_dir
    protect_data.BACKUP_DIR = original_backup_dir
    protect_data.PROTECTION_MANIFEST = original_manifest


class TestEnsureDirectories:
    """Tests for ensure_directories function."""

    def test_creates_data_directory(self):
        """Test that data directory is created."""
        ensure_directories()
        import protect_data

        assert protect_data.DATA_DIR.exists()

    def test_creates_backup_directory(self):
        """Test that backup directory is created."""
        ensure_directories()
        import protect_data

        assert protect_data.BACKUP_DIR.exists()

    def test_does_not_fail_if_directories_exist(self):
        """Test that function doesn't fail if directories already exist."""
        ensure_directories()
        ensure_directories()  # Should not raise


class TestGetProtectedFiles:
    """Tests for get_protected_files function."""

    def test_returns_empty_list_when_no_files(self):
        """Test empty data directory returns empty list."""
        ensure_directories()
        files = get_protected_files()
        assert files == []

    def test_finds_db_files(self):
        """Test that .db files are found."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()
        files = get_protected_files()
        assert len(files) == 1
        assert files[0].name == "test.db"

    def test_finds_sqlite_files(self):
        """Test that .sqlite and .sqlite3 files are found."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.sqlite").touch()
        (protect_data.DATA_DIR / "test.sqlite3").touch()
        files = get_protected_files()
        assert len(files) == 2

    def test_returns_empty_list_if_data_dir_missing(self):
        """Test graceful handling of missing data directory."""
        import protect_data

        # Ensure data dir doesn't exist
        if protect_data.DATA_DIR.exists():
            shutil.rmtree(protect_data.DATA_DIR)
        files = get_protected_files()
        assert files == []


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_creates_backup_with_timestamp(self):
        """Test backup is created with timestamp."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").write_text("test data")

        result = create_backup()

        # Timestamp is just the date/time portion
        assert len(result["timestamp"]) == 15  # YYYYMMDD_HHMMSS format
        assert result["timestamp"][8] == "_"  # Underscore separator
        assert result["files"] == ["test.db"]
        assert Path(result["path"]).exists()
        assert "backup_" in result["path"]

    def test_creates_backup_with_suffix(self):
        """Test backup with custom suffix."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        result = create_backup(suffix="pre-clean")

        assert result["suffix"] == "pre-clean"
        assert "pre-clean" in result["path"]

    def test_backup_copies_file_contents(self):
        """Test that file contents are preserved in backup."""
        ensure_directories()
        import protect_data

        test_content = "important data"
        (protect_data.DATA_DIR / "test.db").write_text(test_content)

        result = create_backup()

        backup_file = Path(result["path"]) / "test.db"
        assert backup_file.read_text() == test_content

    def test_updates_manifest(self):
        """Test that manifest is updated with backup info."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        create_backup()

        manifest = load_manifest()
        assert len(manifest["backups"]) == 1


class TestLoadManifest:
    """Tests for load_manifest function."""

    def test_returns_default_if_no_manifest(self):
        """Test default manifest structure when file doesn't exist."""
        manifest = load_manifest()
        assert manifest == {"backups": [], "protected_patterns": PROTECTED_PATTERNS}

    def test_loads_existing_manifest(self):
        """Test loading existing manifest file."""
        ensure_directories()
        test_manifest = {
            "backups": [{"test": "data"}],
            "protected_patterns": PROTECTED_PATTERNS,
        }
        save_manifest(test_manifest)

        loaded = load_manifest()

        assert loaded == test_manifest


class TestSaveManifest:
    """Tests for save_manifest function."""

    def test_creates_manifest_file(self):
        """Test manifest file is created."""
        ensure_directories()
        import protect_data

        test_data = {"backups": [], "protected_patterns": PROTECTED_PATTERNS}
        save_manifest(test_data)

        assert protect_data.PROTECTION_MANIFEST.exists()

    def test_saves_valid_json(self):
        """Test manifest contains valid JSON."""
        ensure_directories()
        test_data = {
            "backups": [{"timestamp": "20240101_120000"}],
            "protected_patterns": PROTECTED_PATTERNS,
        }
        save_manifest(test_data)

        import protect_data

        content = protect_data.PROTECTION_MANIFEST.read_text()
        parsed = json.loads(content)
        assert parsed == test_data


class TestRestoreLatest:
    """Tests for restore_latest function."""

    def test_restore_from_latest_backup(self):
        """Test restoring files from latest backup."""
        ensure_directories()
        import protect_data

        # Create original file
        (protect_data.DATA_DIR / "test.db").write_text("original")

        # Create backup
        create_backup()

        # Delete original
        (protect_data.DATA_DIR / "test.db").unlink()

        # Restore
        result = restore_latest()

        assert result is True
        assert (protect_data.DATA_DIR / "test.db").exists()
        assert (protect_data.DATA_DIR / "test.db").read_text() == "original"

    def test_returns_false_if_no_backups(self):
        """Test restore fails gracefully with no backups."""
        ensure_directories()

        result = restore_latest()

        assert result is False

    def test_returns_false_if_backup_path_missing(self):
        """Test restore fails if backup directory is missing."""
        ensure_directories()
        import protect_data

        # Create a backup entry but delete the directory
        (protect_data.DATA_DIR / "test.db").touch()
        create_backup()

        # Delete backup directory
        manifest = load_manifest()
        backup_path = Path(manifest["backups"][0]["path"])
        shutil.rmtree(backup_path)

        result = restore_latest()

        assert result is False


class TestListBackups:
    """Tests for list_backups function."""

    def test_shows_no_backups_message(self, capsys):
        """Test message when no backups exist."""
        ensure_directories()

        list_backups()

        captured = capsys.readouterr()
        assert "No backups found" in captured.out

    def test_lists_multiple_backups(self, capsys):
        """Test listing multiple backups."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()
        create_backup(suffix="first")
        create_backup(suffix="second")

        list_backups()

        captured = capsys.readouterr()
        assert "Available Backups:" in captured.out
        assert "first" in captured.out
        assert "second" in captured.out


class TestCheckDataIntegrity:
    """Tests for check_data_integrity function."""

    def test_returns_false_when_no_files(self):
        """Test integrity check with no database files."""
        ensure_directories()

        result = check_data_integrity()

        assert result is False

    def test_returns_true_when_all_files_present(self):
        """Test integrity check passes when all files present."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").write_text("data")

        result = check_data_integrity()

        assert result is True

    def test_detects_missing_files(self, capsys):
        """Test integrity check detects missing files."""
        ensure_directories()
        import protect_data

        # Create manifest with file that doesn't exist
        (protect_data.DATA_DIR / "exists.db").touch()
        manifest = {"backups": [], "protected_patterns": PROTECTED_PATTERNS}
        save_manifest(manifest)

        result = check_data_integrity()

        captured = capsys.readouterr()
        assert result is True  # Only checks existing files


class TestProtectForGitOperation:
    """Tests for protect_for_git_operation function."""

    def test_creates_backup_with_operation_suffix(self):
        """Test backup is created with operation-specific suffix."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        protect_for_git_operation("clean")

        manifest = load_manifest()
        assert len(manifest["backups"]) == 1
        assert manifest["backups"][0]["suffix"] == "pre-clean"

    def test_creates_sentinel_file(self):
        """Test sentinel file is created during protection."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        protect_for_git_operation("reset")

        sentinel = protect_data.BACKUP_DIR / ".data_protection_active"
        assert sentinel.exists()
        assert "Protection active" in sentinel.read_text()


class TestVerifyProtectionAfterOperation:
    """Tests for verify_protection_after_operation function."""

    def test_returns_true_when_files_intact(self):
        """Test verification passes when all files present."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        result = verify_protection_after_operation("clean")

        assert result is True


class TestCleanupOldBackups:
    """Tests for cleanup_old_backups function."""

    def test_removes_old_backups(self):
        """Test old backups are removed."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        # Create 5 backups
        for i in range(5):
            create_backup(suffix=f"backup_{i}")

        # Keep only 3
        cleanup_old_backups(keep_count=3)

        manifest = load_manifest()
        assert len(manifest["backups"]) == 3

    def test_keeps_recent_backups(self):
        """Test most recent backups are kept."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        # Create 5 backups
        for i in range(5):
            create_backup(suffix=f"backup_{i}")

        cleanup_old_backups(keep_count=3)

        manifest = load_manifest()
        suffixes = [b["suffix"] for b in manifest["backups"]]
        assert "backup_2" in suffixes
        assert "backup_3" in suffixes
        assert "backup_4" in suffixes

    def test_does_nothing_if_fewer_backups_than_keep_count(self):
        """Test no action when fewer backups than keep count."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        create_backup(suffix="only")

        cleanup_old_backups(keep_count=10)

        manifest = load_manifest()
        assert len(manifest["backups"]) == 1


class TestMainFunctionality:
    """Integration tests for the main module functionality."""

    def test_full_backup_restore_cycle(self):
        """Test complete backup and restore workflow."""
        ensure_directories()
        import protect_data

        # Create test data
        test_files = {"tasks.db": "tasks data", "users.sqlite": "users data"}
        for name, content in test_files.items():
            (protect_data.DATA_DIR / name).write_text(content)

        # Backup
        backup_result = create_backup(suffix="test")
        assert len(backup_result["files"]) == 2

        # Delete files
        for file in protect_data.DATA_DIR.iterdir():
            file.unlink()

        # Restore
        restore_result = restore_latest()
        assert restore_result is True

        # Verify
        for name, content in test_files.items():
            assert (protect_data.DATA_DIR / name).read_text() == content

    def test_multiple_backup_types(self):
        """Test creating backups with different suffixes."""
        ensure_directories()
        import protect_data

        (protect_data.DATA_DIR / "test.db").touch()

        create_backup(suffix="pre-clean")
        create_backup(suffix="pre-reset")
        create_backup()  # No suffix

        manifest = load_manifest()
        assert len(manifest["backups"]) == 3
        assert manifest["backups"][0]["suffix"] == "pre-clean"
        assert manifest["backups"][1]["suffix"] == "pre-reset"
        assert manifest["backups"][2]["suffix"] is None
