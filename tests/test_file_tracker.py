"""Tests for file_tracker.py"""

import hashlib
from pathlib import Path
import pytest
from file_tracker import FileTracker, FileChange


class TestFileTracker:
    """Test FileTracker class"""

    def test_init(self, temp_dir):
        """Test FileTracker initialization"""
        tracker = FileTracker(str(temp_dir))
        assert tracker.working_directory == temp_dir
        assert len(tracker.tracked_files) == 0
        assert len(tracker.changes) == 0
        assert len(tracker.read_files) == 0

    def test_hash_file(self, temp_dir, sample_files):
        """Test file hashing"""
        tracker = FileTracker(str(temp_dir))
        test_file = temp_dir / "test.py"

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

        # Test hash calculation
        file_hash = tracker._hash_file(test_file)
        assert file_hash == expected_hash

    def test_hash_nonexistent_file(self, temp_dir):
        """Test hashing non-existent file returns None"""
        tracker = FileTracker(str(temp_dir))
        nonexistent = temp_dir / "nonexistent.txt"
        assert tracker._hash_file(nonexistent) is None

    def test_get_file_size(self, temp_dir, sample_files):
        """Test file size calculation"""
        tracker = FileTracker(str(temp_dir))
        test_file = temp_dir / "test.py"

        size = tracker._get_file_size(test_file)
        assert size == test_file.stat().st_size

    def test_track_file(self, temp_dir, sample_files):
        """Test tracking a file"""
        tracker = FileTracker(str(temp_dir))
        tracker.track_file("test.py")

        assert "test.py" in tracker.tracked_files
        assert tracker.tracked_files["test.py"] is not None

    def test_record_read(self, temp_dir, sample_files):
        """Test recording file reads"""
        tracker = FileTracker(str(temp_dir))
        tracker.record_read("test.py")

        assert "test.py" in tracker.read_files
        assert "test.py" in tracker.tracked_files

    def test_detect_file_modification(self, temp_dir, sample_files):
        """Test detecting file modifications"""
        tracker = FileTracker(str(temp_dir))

        # Track file
        tracker.track_file("test.py")

        # Modify file
        test_file = temp_dir / "test.py"
        test_file.write_text("def test_main():\n    assert False\n")

        # Check changes
        changes = tracker.check_changes()

        assert len(changes) > 0
        modified_change = next((c for c in changes if c.action == 'modified'), None)
        assert modified_change is not None
        assert modified_change.path == "test.py"
        assert modified_change.before_hash != modified_change.after_hash

    def test_detect_file_creation(self, temp_dir, sample_files):
        """Test detecting new file creation"""
        tracker = FileTracker(str(temp_dir))

        # Track existing files
        tracker.track_file("test.py")

        # Create new file
        new_file = temp_dir / "new_file.py"
        new_file.write_text("print('new file')\n")

        # Check changes
        changes = tracker.check_changes()

        created_changes = [c for c in changes if c.action == 'created']
        assert len(created_changes) > 0

        new_file_change = next((c for c in created_changes if c.path == "new_file.py"), None)
        assert new_file_change is not None
        assert new_file_change.before_hash is None
        assert new_file_change.after_hash is not None

    def test_detect_file_deletion(self, temp_dir, sample_files):
        """Test detecting file deletion"""
        tracker = FileTracker(str(temp_dir))

        # Track file
        tracker.track_file("test.py")

        # Delete file
        test_file = temp_dir / "test.py"
        test_file.unlink()

        # Check changes
        changes = tracker.check_changes()

        deleted_change = next((c for c in changes if c.action == 'deleted'), None)
        assert deleted_change is not None
        assert deleted_change.path == "test.py"
        assert deleted_change.before_hash is not None
        assert deleted_change.after_hash is None

    def test_get_summary(self, temp_dir, sample_files):
        """Test getting change summary"""
        tracker = FileTracker(str(temp_dir))

        # Track and modify
        tracker.track_file("test.py")
        tracker.record_read("main.py")

        # Modify tracked file
        test_file = temp_dir / "test.py"
        test_file.write_text("modified content\n")

        # Create new file
        new_file = temp_dir / "new.py"
        new_file.write_text("new file\n")

        # Check changes and get summary
        tracker.check_changes()
        summary = tracker.get_summary()

        assert 'total_changes' in summary
        assert 'files_created' in summary
        assert 'files_modified' in summary
        assert 'files_deleted' in summary
        assert 'files_read' in summary
        assert summary['files_read'] > 0

    def test_reset(self, temp_dir, sample_files):
        """Test resetting tracker state"""
        tracker = FileTracker(str(temp_dir))

        tracker.track_file("test.py")
        tracker.record_read("main.py")
        tracker.check_changes()

        # Reset
        tracker.reset()

        assert len(tracker.tracked_files) == 0
        assert len(tracker.changes) == 0
        assert len(tracker.read_files) == 0

    def test_summary_detailed_changes(self, temp_dir, sample_files):
        """Test detailed changes in summary"""
        tracker = FileTracker(str(temp_dir))

        tracker.track_file("test.py")
        test_file = temp_dir / "test.py"
        original_size = test_file.stat().st_size

        # Modify file
        test_file.write_text("def test_main():\n    assert False\n    print('more code')\n")

        tracker.check_changes()
        summary = tracker.get_summary()

        assert 'detailed_changes' in summary
        assert len(summary['detailed_changes']) > 0

        change = summary['detailed_changes'][0]
        assert 'path' in change
        assert 'action' in change
        assert 'timestamp' in change
        assert 'before_hash' in change
        assert 'after_hash' in change
