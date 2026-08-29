"""Deterministic repository scanner for Repository Quality Auditor."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any
from urllib.parse import quote

from auditor.models.models import (
    RepositoryProfile,
    Evidence,
    EvidenceType,
)


# Default directories to ignore during scanning
DEFAULT_IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "target",
    "coverage",
    ".idea",
    ".vscode",
}

# File extensions for source code (non-exhaustive)
SOURCE_EXTENSIONS: Set[str] = {
    # Python
    ".py",
    ".pyi",
    # Java/JVM
    ".java",
    ".class",
    ".jar",
    ".kt",
    ".kts",
    ".scala",
    ".clj",
    # JavaScript/TypeScript
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    # Web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    # Go
    ".go",
    # Rust
    ".rs",
    # C/C++
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".hh",
    ".cxx",
    ".hxx",
    # C#
    ".cs",
    # PHP
    ".php",
    # Ruby
    ".rb",
    # Swift
    ".swift",
    # Kotlin (already included)
    # Scala (already included)
}

# File extensions for documentation
DOCUMENTATION_EXTENSIONS: Set[str] = {
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    ".asciidoc",
    ".markdown",
    ".org",
    ".pdf",
}

# File extensions for configuration
CONFIGURATION_EXTENSIONS: Set[str] = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".config",
    ".xml",
    ".properties",
    ".env",
    ".example",
    ".sample",
}

# Test file patterns (glob-style)
TEST_PATTERNS: Set[str] = {
    "test_*.py",
    "*_test.py",
    "*_test.go",
    "test_*.js",
    "*_test.js",
    "*.test.js",
    "*.spec.js",
    "test_*.ts",
    "*_test.ts",
    "*.test.ts",
    "*.spec.ts",
    "*Test.java",
    "*Tests.java",
    "*Test.scala",
    "*Tests.scala",
}


@dataclass
class ScanOptions:
    """Options for repository scanning."""
    ignored_directories: Set[str] = field(default_factory=lambda: DEFAULT_IGNORED_DIRECTORIES.copy())
    follow_symlinks: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10 MB default limit for reading file content


class RepositoryScanner:
    """Deterministic repository scanner that collects metadata and evidence."""

    def __init__(self, options: ScanOptions | None = None) -> None:
        """Initialize scanner with options."""
        self.options = options or ScanOptions()

    def scan(self, repository_path: str) -> Tuple[RepositoryProfile, List[Evidence]]:
        """
        Scan a repository and return its profile and evidence.

        Args:
            repository_path: Path to the repository to scan

        Returns:
            Tuple of (RepositoryProfile, List[Evidence])

        Raises:
            ValueError: If the path is invalid or not a directory
            PermissionError: If access is denied
            OSError: For other filesystem errors
        """
        # Validate and resolve the path
        repo_path = self._validate_path(repository_path)

        # Initialize counters and collections
        file_count = 0
        dir_count = 0
        source_file_count = 0
        test_file_count = 0
        evidence_list: List[Evidence] = []

        # Track detected special files and directories
        detected_files: Set[str] = set()
        detected_directories: Set[str] = set()

        # Walk the repository
        for root, dirs, files in os.walk(
            repo_path,
            topdown=True,
            followlinks=self.options.follow_symlinks,
            onerror=self._on_walk_error,
        ):
            # Skip ignored directories (modify dirs in-place to prevent walking into them)
            dirs[:] = [d for d in dirs if d not in self.options.ignored_directories]

            # Update directory count (excluding ignored ones)
            dir_count += len(dirs)

            # Process files in current directory
            for file_name in files:
                file_path = Path(root) / file_name
                relative_path = file_path.relative_to(repo_path)

                # Skip if file is in an ignored directory (should be caught by dirs filtering, but double-check)
                if any(part in self.options.ignored_directories for part in relative_path.parts):
                    continue

                file_count += 1

                # Check if it's a source file
                if self._is_source_file(file_name):
                    source_file_count += 1

                # Check if it's a test file
                if self._is_test_file(file_name):
                    test_file_count += 1

                # Detect special files (by name, not extension)
                self._detect_special_file(file_name, detected_files, evidence_list)

            # Detect special directories (by name)
            for dir_name in dirs:
                self._detect_special_directory(dir_name, detected_directories, evidence_list)

        # Generate evidence for detected special files and directories
        evidence_list.extend(self._generate_evidence_for_detected_items(
            detected_files, detected_directories, repo_path
        ))

        # Create repository profile
        profile = RepositoryProfile(
            name=repo_path.name,
            url=None,  # Scanner doesn't detect remote URL
            description=None,  # Scanner doesn't auto-generate description
            language=self._detect_primary_language(source_file_count, test_file_count),
            stars=None,
            size_kb=self._get_directory_size(repo_path),
            file_count=file_count,
            created_at=None,  # Scanner doesn't detect creation time
            updated_at=None,  # Scanner doesn't detect modification time
            topics=[],  # Scanner doesn't detect topics
            license=None,  # Scanner doesn't detect license automatically
            metadata={
                "total_directories": dir_count,
                "source_file_count": source_file_count,
                "test_file_count": test_file_count,
                "scanner_version": "0.1.0",
            },
        )

        return profile, evidence_list

    def _validate_path(self, repository_path: str) -> Path:
        """Validate and resolve the repository path."""
        path = Path(repository_path).resolve()

        if not path.exists():
            raise ValueError(f"Repository path does not exist: {repository_path}")

        if not path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repository_path}")

        # Check if we can read the directory
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Permission denied: cannot read directory {repository_path}")

        return path

    def _on_walk_error(self, error: OSError) -> None:
        """Handle errors during directory walk."""
        # We'll just skip the problematic directory and continue
        # In a real implementation, we might log this or add evidence about access issues
        pass

    def _is_source_file(self, filename: str) -> bool:
        """Check if a file is a source file based on extension."""
        return any(filename.lower().endswith(ext) for ext in SOURCE_EXTENSIONS)

    def _is_test_file(self, filename: str) -> bool:
        """Check if a file is a test file based on name patterns."""
        # Simple pattern matching - for production we might use fnmatch or regex
        lower_name = filename.lower()
        for pattern in TEST_PATTERNS:
            # Convert glob pattern to simple check
            if pattern == "test_*.py":
                if lower_name.startswith("test_") and lower_name.endswith(".py"):
                    return True
            elif pattern == "*_test.py":
                if lower_name.endswith("_test.py"):
                    return True
            elif pattern == "*_test.go":
                if lower_name.endswith("_test.go"):
                    return True
            elif pattern == "test_*.js":
                if lower_name.startswith("test_") and lower_name.endswith(".js"):
                    return True
            elif pattern == "*_test.js":
                if lower_name.endswith("_test.js"):
                    return True
            elif pattern == "*.test.js":
                if lower_name.endswith(".test.js"):
                    return True
            elif pattern == "*.spec.js":
                if lower_name.endswith(".spec.js"):
                    return True
            elif pattern == "test_*.ts":
                if lower_name.startswith("test_") and lower_name.endswith(".ts"):
                    return True
            elif pattern == "*_test.ts":
                if lower_name.endswith("_test.ts"):
                    return True
            elif pattern == "*.test.ts":
                if lower_name.endswith(".test.ts"):
                    return True
            elif pattern == "*.spec.ts":
                if lower_name.endswith(".spec.ts"):
                    return True
            elif pattern == "*Test.java":
                if lower_name.endswith("test.java"):
                    return True
            elif pattern == "*Tests.java":
                if lower_name.endswith("tests.java"):
                    return True
            elif pattern == "*Test.scala":
                if lower_name.endswith("test.scala"):
                    return True
            elif pattern == "*Tests.scala":
                if lower_name.endswith("tests.scala"):
                    return True
        return False

    def _detect_special_file(
        self, filename: str, detected_files: Set[str], evidence_list: List[Evidence]
    ) -> None:
        """Detect special files by name and prepare evidence generation."""
        special_files = {
            "README.md",
            "README.rst",
            "README.txt",
            "README",
            ".gitignore",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "go.mod",
            "Cargo.toml",
            ".env",
            ".env.example",
        }

        if filename in special_files:
            detected_files.add(filename)

    def _detect_special_directory(
        self, dirname: str, detected_directories: Set[str], evidence_list: List[Evidence]
    ) -> None:
        """Detect special directories by name."""
        special_directories = {
            "src",
            "test",
            "tests",
            "docs",
            ".github",
            ".github/workflows",
        }

        if dirname in special_directories:
            detected_directories.add(dirname)

    def _generate_evidence_for_detected_items(
        self,
        detected_files: Set[str],
        detected_directories: Set[str],
        repo_path: Path,
    ) -> List[Evidence]:
        """Generate Evidence objects for detected special files and directories."""
        evidence_list: List[Evidence] = []

        # Evidence for special files
        file_evidence_map = {
            "README.md": ("README exists", "README.md file found in repository root"),
            "README.rst": ("README exists", "README.rst file found in repository root"),
            "README.txt": ("README exists", "README.txt file found in repository root"),
            "README": ("README exists", "README file found in repository root"),
            ".gitignore": ("Git ignore file exists", ".gitignore file found in repository root"),
            "Dockerfile": ("Dockerfile exists", "Dockerfile found in repository root"),
            "docker-compose.yml": ("Docker compose exists", "docker-compose.yml found in repository root"),
            "docker-compose.yaml": ("Docker compose exists", "docker-compose.yaml found in repository root"),
            "pyproject.toml": ("Python project file exists", "pyproject.toml found in repository root"),
            "requirements.txt": ("Python requirements exists", "requirements.txt found in repository root"),
            "package.json": ("Node.js package exists", "package.json found in repository root"),
            "pom.xml": ("Maven project exists", "pom.xml found in repository root"),
            "build.gradle": ("Gradle project exists", "build.gradle found in repository root"),
            "build.gradle.kts": ("Gradle Kotlin project exists", "build.gradle.kts found in repository root"),
            "go.mod": ("Go module exists", "go.mod found in repository root"),
            "Cargo.toml": ("Rust Cargo project exists", "Cargo.toml found in repository root"),
        }

        for filename in detected_files:
            if filename in file_evidence_map:
                title, description = file_evidence_map[filename]
                evidence_list.append(
                    Evidence(
                        id=self._generate_evidence_id("file", filename),
                        type=EvidenceType.FILE_CONTENT,
                        source=str(filename),
                        content=title,  # We're not reading file content for security
                        metadata={"file_path": filename, "detected": True},
                    )
                )

        # Evidence for special directories
        dir_evidence_map = {
            "src": ("Source directory exists", "src/ directory found in repository"),
            "test": ("Test directory exists", "test/ directory found in repository"),
            "tests": ("Test directory exists", "tests/ directory found in repository"),
            "docs": ("Documentation directory exists", "docs/ directory found in repository"),
            ".github": ("GitHub directory exists", ".github/ directory found in repository"),
            ".github/workflows": ("GitHub workflows exist", ".github/workflows/ directory found in repository"),
        }

        for dirname in detected_directories:
            if dirname in dir_evidence_map:
                title, description = dir_evidence_map[dirname]
                evidence_list.append(
                    Evidence(
                        id=self._generate_evidence_id("dir", dirname),
                        type=EvidenceType.STRUCTURE,
                        source=dirname,
                        content=title,
                        metadata={"directory_path": dirname, "detected": True},
                    )
                )

        # Generate negative evidence (what's missing)
        # We'll do this for a few key items to demonstrate the pattern
        key_files = {"README.md", ".gitignore", "Dockerfile", "pyproject.toml"}
        for filename in key_files:
            if filename not in detected_files:
                evidence_list.append(
                    Evidence(
                        id=self._generate_evidence_id("missing", filename),
                        type=EvidenceType.METADATA,
                        source=filename,
                        content=f"{filename} missing",
                        metadata={"file_path": filename, "detected": False},
                    )
                )

        key_dirs = {"src", "tests", ".github/workflows"}
        for dirname in key_dirs:
            if dirname not in detected_directories:
                evidence_list.append(
                    Evidence(
                        id=self._generate_evidence_id("missing", dirname),
                        type=EvidenceType.METADATA,
                        source=dirname,
                        content=f"{dirname} directory missing",
                        metadata={"directory_path": dirname, "detected": False},
                    )
                )

        return evidence_list

    def _generate_evidence_id(self, prefix: str, identifier: str) -> str:
        """Generate a deterministic evidence ID."""
        # Simple hash-based ID for demonstration
        import hashlib
        data = f"{prefix}:{identifier}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]

    def _detect_primary_language(self, source_count: int, test_count: int) -> str | None:
        """Detect primary programming language based on file counts (simplified)."""
        # This is a very basic implementation - in reality we'd check file extensions
        # For now, we'll return None as we're not doing language detection yet
        return None

    def _get_directory_size(self, path: Path) -> int | None:
        """Get the size of the directory in kilobytes."""
        try:
            total_size = 0
            for entry in path.rglob("*"):
                if entry.is_file() and not any(
                    part in self.options.ignored_directories for part in entry.relative_to(path).parts
                ):
                    try:
                        total_size += entry.stat().st_size
                    except (OSError, PermissionError):
                        # Skip files we can't read
                        pass
            return total_size // 1024  # Convert to KB
        except (OSError, PermissionError):
            return None