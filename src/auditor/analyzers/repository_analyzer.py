"""Repository analyzer for generating findings from scanner evidence."""

from typing import List
from auditor.models.models import (
    RepositoryProfile,
    Evidence,
    EvidenceType,
    Finding,
    FindingCategory,
    FindingSeverity,
)


class RepositoryAnalyzer:
    """Analyzes repository profile and evidence to generate structured findings."""

    def analyze(
        self,
        profile: RepositoryProfile,
        evidence: List[Evidence],
    ) -> List[Finding]:
        """
        Analyze repository profile and evidence to generate findings.

        Args:
            profile: Repository profile from scanner
            evidence: List of evidence collected during scan

        Returns:
            List of findings generated from analysis
        """
        findings = []

        # Extract useful information from evidence for rule evaluation
        detected_readme = self._has_readme(evidence)
        detected_test_files = profile.metadata.get("test_file_count", 0) > 0
        detected_dockerfile = self._has_dockerfile(evidence)
        detected_dependency_manifest = self._has_dependency_manifest(evidence)
        detected_source_files = profile.metadata.get("source_file_count", 0) > 0

        # DOC-001: README is missing
        if not detected_readme:
            readme_evidence_ids = self._get_evidence_ids_for_missing_readme(evidence)
            findings.append(
                Finding(
                    id=self._generate_finding_id("DOC-001"),
                    rule_id="DOC-001",
                    title="README file is missing",
                    description="No recognized README file was detected in the repository.",
                    category=FindingCategory.DOCUMENTATION,
                    severity=FindingSeverity.MEDIUM,
                    evidence_ids=readme_evidence_ids,
                )
            )

        # TEST-001: No test files detected
        if not detected_test_files:
            test_evidence_ids = self._get_evidence_ids_for_test_files(evidence, profile)
            findings.append(
                Finding(
                    id=self._generate_finding_id("TEST-001"),
                    rule_id="TEST-001",
                    title="No test files detected",
                    description="No test files were detected in the repository.",
                    category=FindingCategory.TESTING,
                    severity=FindingSeverity.HIGH,
                    evidence_ids=test_evidence_ids,
                )
            )

        # CONT-001: Dockerfile is missing
        if not detected_dockerfile:
            dockerfile_evidence_ids = self._get_evidence_ids_for_missing_dockerfile(evidence)
            findings.append(
                Finding(
                    id=self._generate_finding_id("CONT-001"),
                    rule_id="CONT-001",
                    title="Dockerfile is missing",
                    description="No Dockerfile was detected in the repository root.",
                    category=FindingCategory.CONTAINERIZATION,
                    severity=FindingSeverity.LOW,
                    evidence_ids=dockerfile_evidence_ids,
                )
            )

        # DEP-001: No recognized dependency manifest detected
        if not detected_dependency_manifest:
            dep_evidence_ids = self._get_evidence_ids_for_missing_dependency(evidence)
            findings.append(
                Finding(
                    id=self._generate_finding_id("DEP-001"),
                    rule_id="DEP-001",
                    title="No dependency manifest detected",
                    description="No recognized dependency manifest was detected in the repository.",
                    category=FindingCategory.DEPENDENCY,
                    severity=FindingSeverity.MEDIUM,
                    evidence_ids=dep_evidence_ids,
                )
            )

        # STRUCT-001: No source files detected
        if not detected_source_files:
            struct_evidence_ids = self._get_evidence_ids_for_missing_source(evidence, profile)
            findings.append(
                Finding(
                    id=self._generate_finding_id("STRUCT-001"),
                    rule_id="STRUCT-001",
                    title="No source files detected",
                    description="No source files were detected in the repository.",
                    category=FindingCategory.STRUCTURE,
                    severity=FindingSeverity.MEDIUM,
                    evidence_ids=struct_evidence_ids,
                )
            )

        return findings

    def _has_readme(self, evidence: List[Evidence]) -> bool:
        """Check if README evidence exists and is detected."""
        for ev in evidence:
            if (
                ev.source in ["README.md", "README.rst", "README.txt", "README"]
                and ev.metadata.get("detected", False) is True
            ):
                return True
        return False

    def _has_dockerfile(self, evidence: List[Evidence]) -> bool:
        """Check if Dockerfile evidence exists and is detected."""
        for ev in evidence:
            if ev.source == "Dockerfile" and ev.metadata.get("detected", False) is True:
                return True
        return False

    def _has_dependency_manifest(self, evidence: List[Evidence]) -> bool:
        """Check if any dependency manifest evidence exists and is detected."""
        dependency_files = {
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "go.mod",
            "Cargo.toml",
            "pyproject.toml",  # Also counts as dependency manifest
        }
        for ev in evidence:
            if (
                ev.source in dependency_files
                and ev.metadata.get("detected", False) is True
                and ev.type == EvidenceType.FILE_CONTENT
            ):
                return True
        return False

    def _get_evidence_ids_for_missing_readme(self, evidence: List[Evidence]) -> List[str]:
        """Get evidence IDs for missing README."""
        ids = []
        readme_variants = ["README.md", "README.rst", "README.txt", "README"]
        for ev in evidence:
            if (
                ev.source in readme_variants
                and ev.metadata.get("detected", True) is False
                and ev.type == EvidenceType.METADATA
            ):
                ids.append(ev.id)
        return ids

    def _get_evidence_ids_for_test_files(self, evidence: List[Evidence], profile: RepositoryProfile) -> List[str]:
        """Get evidence IDs related to test files (or lack thereof)."""
        ids = []
        # If we have test files, we might want to reference the evidence that showed them
        # For now, if no test files, we can reference missing test directory evidence
        if profile.metadata.get("test_file_count", 0) == 0:
            for ev in evidence:
                if (
                    ev.source in ["test", "tests"]
                    and ev.metadata.get("detected", True) is False
                    and ev.type == EvidenceType.METADATA
                ):
                    ids.append(ev.id)
        return ids

    def _get_evidence_ids_for_missing_dockerfile(self, evidence: List[Evidence]) -> List[str]:
        """Get evidence IDs for missing Dockerfile."""
        ids = []
        for ev in evidence:
            if (
                ev.source == "Dockerfile"
                and ev.metadata.get("detected", True) is False
                and ev.type == EvidenceType.METADATA
            ):
                ids.append(ev.id)
        return ids

    def _get_evidence_ids_for_missing_dependency(self, evidence: List[Evidence]) -> List[str]:
        """Get evidence IDs for missing dependency manifests."""
        ids = []
        dependency_files = {
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "go.mod",
            "Cargo.toml",
            "pyproject.toml",
        }
        for ev in evidence:
            if (
                ev.source in dependency_files
                and ev.metadata.get("detected", True) is False
                and ev.type == EvidenceType.METADATA
            ):
                ids.append(ev.id)
        return ids

    def _get_evidence_ids_for_missing_source(self, evidence: List[Evidence], profile: RepositoryProfile) -> List[str]:
        """Get evidence IDs for missing source files."""
        ids = []
        # If no source files, we might reference missing source directory or lack of source file evidence
        if profile.metadata.get("source_file_count", 0) == 0:
            for ev in evidence:
                if (
                    ev.source == "src"
                    and ev.metadata.get("detected", True) is False
                    and ev.type == EvidenceType.METADATA
                ):
                    ids.append(ev.id)
        return ids

    def _generate_finding_id(self, rule_id: str) -> str:
        """Generate a deterministic finding ID based on rule ID."""
        import hashlib
        return hashlib.sha256(rule_id.encode("utf-8")).hexdigest()[:16]