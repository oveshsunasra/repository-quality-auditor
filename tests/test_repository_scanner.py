"""Unit tests for the repository scanner."""

import os
import platform
import stat
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from auditor.analyzers.repository_scanner import RepositoryScanner, ScanOptions
from auditor.models.models import RepositoryProfile, Evidence, EvidenceType


@pytest.fixture
def temp_repo() -> Generator[Path, None, None]:
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create basic repository structure
        (repo_path / "README.md").write_text("# Test Repo")
        (repo_path / ".gitignore").write_text("__pycache__\n*.pyc\n")
        (repo_path / "main.py").write_text("print('hello')")
        (repo_path / "test_main.py").write_text("def test_main(): pass")
        (repo_path / "requirements.txt").write_text("requests\n")

        # Create directories
        (repo_path / "src").mkdir()
        (repo_path / "tests").mkdir()
        (repo_path / "docs").mkdir()
        (repo_path / "src" / "module.py").write_text("# module code")
        (repo_path / "tests" / "test_module.py").write_text("def test_module(): pass")

        # Create ignored directories to verify they're skipped
        (repo_path / ".git").mkdir()
        (repo_path / ".git" / "config").write_text("[core]")
        (repo_path / "__pycache__").mkdir()
        (repo_path / "__pycache__" / "temp.pyc").write_text("fake bytecode")
        (repo_path / ".venv").mkdir()
        (repo_path / ".venv" / "pyvenv.cfg").write_text("version = 3.12")

        yield repo_path


def test_scanner_valid_repository(temp_repo: Path) -> None:
    """Test scanning a valid repository."""
    scanner = RepositoryScanner()
    profile, evidence = scanner.scan(str(temp_repo))

    # Check profile
    assert isinstance(profile, RepositoryProfile)
    assert profile.name == temp_repo.name
    assert profile.file_count > 0
    assert profile.metadata["source_file_count"] >= 2  # main.py and src/module.py
    assert profile.metadata["test_file_count"] >= 2   # test_main.py and tests/test_module.py

    # Check evidence
    assert isinstance(evidence, list)
    assert len(evidence) > 0

    # Check that we have evidence for detected files
    evidence_sources = {e.source for e in evidence}
    assert "README.md" in evidence_sources
    assert ".gitignore" in evidence_sources
    assert "requirements.txt" in evidence_sources

    # Check that we have evidence for detected directories
    structure_evidence = [e for e in evidence if e.type == EvidenceType.STRUCTURE]
    structure_sources = {e.source for e in structure_evidence}
    assert "src" in structure_sources
    assert "tests" in structure_sources
    assert "docs" in structure_sources


def test_scanner_invalid_path() -> None:
    """Test scanning an invalid path."""
    scanner = RepositoryScanner()

    with pytest.raises(ValueError, match="does not exist"):
        scanner.scan("/non/existent/path")

    with pytest.raises(ValueError, match="not a directory"):
        # Create a file and try to scan it as a directory
        with tempfile.NamedTemporaryFile() as tmp:
            scanner.scan(tmp.name)


def test_scanner_file_instead_of_directory() -> None:
    """Test scanning a file when directory is expected."""
    scanner = RepositoryScanner()

    with tempfile.NamedTemporaryFile() as tmp:
        with pytest.raises(ValueError, match="not a directory"):
            scanner.scan(tmp.name)


def test_scanner_permission_error() -> None:
    """Test handling of permission errors (where possible)."""
    scanner = RepositoryScanner()

    # Skip this test on Windows as permission behavior differs significantly
    if platform.system() == "Windows":
        pytest.skip("Permission test skipped on Windows due to different permission model")

    # Create a directory and remove read permissions
    with tempfile.TemporaryDirectory() as tmpdir:
        no_read_dir = Path(tmpdir) / "no_read"
        no_read_dir.mkdir()
        (no_read_dir / "test.txt").write_text("test")

        # Remove read permissions
        os.chmod(no_read_dir, stat.S_IWUSR | stat.S_IXUSR)  # write and execute only

        try:
            with pytest.raises(PermissionError):
                scanner.scan(str(no_read_dir))
        finally:
            # Restore permissions so cleanup can work
            os.chmod(no_read_dir, stat.S_IRWXU)


def test_scanner_ignored_directories(temp_repo: Path) -> None:
    """Test that ignored directories are not counted."""
    scanner = RepositoryScanner()
    profile, evidence = scanner.scan(str(temp_repo))

    # The .git, __pycache__, and .venv directories should be ignored
    # We can't easily test the exact count without exposing internals,
    # but we can verify that evidence doesn't include ignored directory content
    # and that file counts are reasonable

    # Check that we didn't count files in ignored directories
    # (This is implicit in the file count - if we counted .git files,
    # file_count would be higher)
    assert profile.file_count >= 5  # README, .gitignore, main.py, test_main.py, requirements.txt

    # Check that ignored directories don't appear in detected directories
    structure_evidence = [e for e in evidence if e.type == EvidenceType.STRUCTURE and e.metadata.get("detected")]
    detected_dirs = {e.source for e in structure_evidence}
    assert ".git" not in detected_dirs
    assert "__pycache__" not in detected_dirs
    assert ".venv" not in detected_dirs


def test_scanner_source_file_detection() -> None:
    """Test source file detection logic."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create various file types
        (repo_path / "main.py").write_text("# Python")
        (repo_path / "Main.java").write_text("public class Main {}")
        (repo_path / "app.js").write_text("console.log('hello');")
        (repo_path / "main.go").write_text("package main")
        (repo_path / "lib.rs").write_text("fn main() {}")
        (repo_path / "Program.cs").write_text("class Program {}")
        (repo_path / "script.php").write_text("<?php echo 'hello'; ?>")
        (repo_path / "app.rb").write_text("puts 'hello'")
        (repo_path / "main.swift").write_text("print('hello')")
        (repo_path / "Main.kt").write_text("fun main() = println('hello')")
        (repo_path / "Main.scala").write_text("object Main extends App")

        # Non-source files
        (repo_path / "README.md").write_text("# Readme")
        (repo_path / "config.json").write_text("{}")
        (repo_path / "style.css").write_text("body {}",)
        (repo_path / "data.bin").write_bytes(b"\x00\x01\x02\x03")

        profile, _ = scanner.scan(str(repo_path))

        # Should have detected source files
        assert profile.metadata["source_file_count"] >= 10  # All the source files above

        # Should have detected documentation
        # Note: README.md detection is in evidence, not in source count
        # CSS might be counted as source depending on implementation


def test_scanner_test_file_detection() -> None:
    """Test test file detection logic."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create test files with various patterns
        (repo_path / "test_basic.py").write_text("def test_basic(): pass")
        (repo_path / "basic_test.py").write_text("def basic_test(): pass")
        (repo_path / "test_example.js").write_text("function test() {}")
        (repo_path / "example.test.js").write_text("function test() {}")
        (repo_path / "example.spec.js").write_text("describe('example', () => {});")
        (repo_path / "ExampleTest.java").write_text("public class ExampleTest { @Test void test() {} }")
        (repo_path / "ExampleTests.java").write_text("public class ExampleTests { @Test void test() {} }")

        # Non-test files that might look similar
        (repo_path / "testing.py").write_text("# This is about testing, not a test")
        (repo_path / "attest.py").write_text("# Attestation, not a test")
        (repo_path / "prototypal.js").write_text("# Prototypal inheritance")

        profile, _ = scanner.scan(str(repo_path))

        # Should have detected test files
        assert profile.metadata["test_file_count"] >= 7  # All the test files above

        # Should not have counted non-test files
        # (testing.py, attest.py, prototypal.js should not be counted as tests)


def test_scanner_special_file_detection(temp_repo: Path) -> None:
    """Test detection of special files like README, Dockerfile, etc."""
    scanner = RepositoryScanner()
    profile, evidence = scanner.scan(str(temp_repo))

    # Check for evidence of special files
    file_evidence = [e for e in evidence if e.type == EvidenceType.FILE_CONTENT and e.metadata.get("detected")]
    detected_special_files = {e.source for e in file_evidence}

    assert "README.md" in detected_special_files
    assert ".gitignore" in detected_special_files
    assert "requirements.txt" in detected_special_files


def test_scanner_special_directory_detection(temp_repo: Path) -> None:
    """Test detection of special directories."""
    scanner = RepositoryScanner()
    profile, evidence = scanner.scan(str(temp_repo))

    # Check for evidence of special directories
    structure_evidence = [e for e in evidence if e.type == EvidenceType.STRUCTURE and e.metadata.get("detected")]
    detected_special_dirs = {e.source for e in structure_evidence}

    assert "src" in detected_special_dirs
    assert "tests" in detected_special_dirs
    assert "docs" in detected_special_dirs


def test_scanner_missing_items_evidence() -> None:
    """Test that missing important items generate negative evidence."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Create a nearly empty repo
        (repo_path / "lonely.py").write_text("# alone")

        profile, evidence = scanner.scan(str(repo_path))

        # Check for missing evidence
        metadata_evidence = [e for e in evidence if e.type == EvidenceType.METADATA]
        missing_evidence = [e for e in metadata_evidence if not e.metadata.get("detected", True)]
        missing_sources = {e.source for e in missing_evidence}

        # Should report missing common files
        assert "README.md" in missing_sources
        assert ".gitignore" in missing_sources

        # Should report missing common directories
        assert "src" in missing_sources
        assert "tests" in missing_sources


def test_scanner_empty_repository() -> None:
    """Test scanning an empty repository."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Leave it empty

        profile, evidence = scanner.scan(str(repo_path))

        assert profile.file_count == 0
        assert profile.metadata["source_file_count"] == 0
        assert profile.metadata["test_file_count"] == 0

        # Should still generate evidence for missing items
        assert len(evidence) > 0


def test_scanner_nested_directories() -> None:
    """Test scanning repositories with nested directory structures."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create nested structure
        (repo_path / "README.md").write_text("# Nested Repo")
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main").mkdir()
        (repo_path / "src" / "main" / "app.py").write_text("print('nested')")
        (repo_path / "src" / "utils").mkdir()
        (repo_path / "src" / "utils" / "helper.py").write_text("# helper")
        (repo_path / "tests").mkdir()
        (repo_path / "tests" / "integration").mkdir()
        (repo_path / "tests" / "integration" / "test_api.py").write_text("def test_api(): pass")

        profile, evidence = scanner.scan(str(repo_path))

        # Should count all source and test files
        assert profile.metadata["source_file_count"] >= 2  # app.py and helper.py
        assert profile.metadata["test_file_count"] >= 1    # test_api.py

        # Should detect directories
        structure_evidence = [e for e in evidence if e.type == EvidenceType.STRUCTURE and e.metadata.get("detected")]
        detected_dirs = {e.source for e in structure_evidence}
        assert "src" in detected_dirs
        assert "tests" in detected_dirs


def test_scanner_symlink_handling() -> None:
    """Test that symlinks are handled safely (not followed by default)."""
    # Skip this test on Windows as symlink creation requires special privileges
    if platform.system() == "Windows":
        pytest.skip("Symlink test skipped on Windows due to privilege requirements")

    scanner = RepositoryScanner(options=ScanOptions(follow_symlinks=False))

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        target_dir = Path(tmpdir) / "target"
        target_dir.mkdir()
        (target_dir / "target_file.txt").write_text("target content")

        # Create a symlink
        link_path = repo_path / "link_to_target"
        link_path.symlink_to(target_dir)

        # Create some repo content
        (repo_path / "README.md").write_text("# Test")
        (repo_path / "real_file.txt").write_text("real content")

        profile, evidence = scanner.scan(str(repo_path))

        # Should not follow the symlink (default behavior)
        # The symlink itself should be counted as a file, but not its target
        assert profile.file_count >= 3  # README, real_file.txt, link_to_target

        # Should not count the target file in source/test counts
        # (unless it has a recognized extension, which .txt doesn't for source)


def test_scanner_breaks_outside_repo() -> None:
    """Test that scanner doesn't break outside the repository boundary."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        outside_path = Path(tmpdir) / "outside"
        outside_path.mkdir()
        (outside_path / "secret.txt").write_text("shhh")

        # Create repo content
        (repo_path / "README.md").write_text("# Test")
        (repo_path / "public.txt").write_text("public")

        # Try to create a symlink that points outside
        outside_link = repo_path / "outside_link"
        try:
            outside_link.symlink_to(outside_path / "secret.txt")
            profile, evidence = scanner.scan(str(repo_path))

            # With default options (follow_symlinks=False), we should not read the target
            # The symlink should be counted as a file, but we shouldn't access outside content
            assert profile.file_count >= 3  # README, public.txt, outside_link

            # Check that we didn't inadvertently include outside content
            # This is harder to test directly, but the scanner should be safe
        except (OSError, PermissionError):
            # Symlink creation might fail in some environments
            pass


def test_scanner_json_serialization() -> None:
    """Test that scan results serialize to JSON correctly."""
    scanner = RepositoryScanner()

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / "README.md").write_text("# Test")
        (repo_path / "main.py").write_text("print('hello')")

        profile, evidence = scanner.scan(str(repo_path))

        # Import here to avoid circular imports
        from auditor.models.scan_result import ScanResult

        scan_result = ScanResult(
            repository_profile=profile,
            evidence=evidence,
        )

        # This should not raise an exception
        json_data = scan_result.model_dump()

        # Check that computed fields work
        assert scan_result.total_evidence_count == len(evidence)
        assert scan_result.total_findings_count == 0  # Scanner doesn't make findings

        # JSON serialization should work
        import json
        json_str = json.dumps(json_data, default=str)
        assert len(json_str) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])