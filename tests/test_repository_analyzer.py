"""Unit tests for repository analyzer."""

import pytest
from auditor.models.models import (
    RepositoryProfile,
    Evidence,
    EvidenceType,
    FindingSeverity,
    FindingCategory,
)
from auditor.analyzers.repository_analyzer import RepositoryAnalyzer


def create_basic_profile(file_count=10, source_count=5, test_count=2):
    """Create a basic repository profile for testing."""
    return RepositoryProfile(
        name="test-repo",
        file_count=file_count,
        metadata={
            "source_file_count": source_count,
            "test_file_count": test_count,
            "total_directories": 3,
        }
    )


def create_evidence(id_suffix, source, evidence_type, detected=True, content=None):
    """Create an evidence object for testing."""
    if content is None:
        if evidence_type == EvidenceType.FILE_CONTENT and detected:
            content = f"{source} exists"
        elif evidence_type == EvidenceType.METADATA and not detected:
            content = f"{source} missing"
        elif evidence_type == EvidenceType.STRUCTURE and detected:
            content = f"{source} directory exists"
        else:
            content = f"{source} evidence"

    return Evidence(
        id=f"ev-{id_suffix}",
        type=evidence_type,
        source=source,
        content=content,
        metadata={"detected": detected, "file_path": source if "." in source else f"{source}/"},
    )


def test_readme_missing_generates_doc_001():
    """Test that missing README generates DOC-001 finding."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", ".gitignore", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("3", "Dockerfile", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("4", "requirements.txt", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("5", "src", EvidenceType.STRUCTURE, detected=True),
        create_evidence("6", "tests", EvidenceType.METADATA, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "DOC-001"
    assert finding.category == FindingCategory.DOCUMENTATION
    assert finding.severity == FindingSeverity.MEDIUM
    assert "README" in finding.title
    assert "recognized" in finding.description.lower()
    assert "detected" in finding.description.lower()
    assert finding.evidence_ids == ["ev-1"]


def test_readme_exists_no_doc_001():
    """Test that existing README does not generate DOC-001."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "README.md", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("2", ".gitignore", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    # Should have no findings (assuming other conditions are met)
    doc_findings = [f for f in findings if f.rule_id == "DOC-001"]
    assert len(doc_findings) == 0


def test_no_test_files_generates_test_001():
    """Test that no test files generates TEST-001 finding."""
    profile = create_basic_profile(test_count=0)  # No test files
    evidence = [
        create_evidence("1", "tests", EvidenceType.METADATA, detected=False),
        create_evidence("2", "src", EvidenceType.STRUCTURE, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    test_findings = [f for f in findings if f.rule_id == "TEST-001"]
    assert len(test_findings) == 1
    finding = test_findings[0]
    assert finding.category == FindingCategory.TESTING
    assert finding.severity == FindingSeverity.HIGH
    assert "test" in finding.title.lower()
    assert finding.evidence_ids == ["ev-1"]


def test_test_files_exist_no_test_001():
    """Test that existing test files do not generate TEST-001."""
    profile = create_basic_profile(test_count=2)  # Has test files
    evidence = [
        create_evidence("1", "tests", EvidenceType.METADATA, detected=True),
        create_evidence("2", "src", EvidenceType.STRUCTURE, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    test_findings = [f for f in findings if f.rule_id == "TEST-001"]
    assert len(test_findings) == 0


def test_dockerfile_missing_generates_cont_001():
    """Test that missing Dockerfile generates CONT-001 finding."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "Dockerfile", EvidenceType.METADATA, detected=False),
        create_evidence("2", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    container_findings = [f for f in findings if f.rule_id == "CONT-001"]
    assert len(container_findings) == 1
    finding = container_findings[0]
    assert finding.category == FindingCategory.CONTAINERIZATION
    assert finding.severity == FindingSeverity.LOW
    assert "dockerfile" in finding.title.lower()
    assert finding.evidence_ids == ["ev-1"]


def test_dockerfile_exists_no_cont_001():
    """Test that existing Dockerfile does not generate CONT-001."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "Dockerfile", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("2", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    container_findings = [f for f in findings if f.rule_id == "CONT-001"]
    assert len(container_findings) == 0


def test_no_dependency_manifest_generates_dep_001():
    """Test that no dependency manifest generates DEP-001 finding."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "requirements.txt", EvidenceType.METADATA, detected=False),
        create_evidence("2", "package.json", EvidenceType.METADATA, detected=False),
        create_evidence("3", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    dependency_findings = [f for f in findings if f.rule_id == "DEP-001"]
    assert len(dependency_findings) == 1
    finding = dependency_findings[0]
    assert finding.category == FindingCategory.DEPENDENCY
    assert finding.severity == FindingSeverity.MEDIUM
    assert "dependency" in finding.title.lower()
    # Should reference missing dependency manifests
    assert set(finding.evidence_ids) == {"ev-1", "ev-2"}


def test_dependency_manifest_exists_no_dep_001():
    """Test that existing dependency manifest does not generate DEP-001."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "requirements.txt", EvidenceType.FILE_CONTENT, detected=True),
        create_evidence("2", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    dependency_findings = [f for f in findings if f.rule_id == "DEP-001"]
    assert len(dependency_findings) == 0


def test_no_source_files_generates_struct_001():
    """Test that no source files generates STRUCT-001 finding."""
    profile = create_basic_profile(source_count=0)  # No source files
    evidence = [
        create_evidence("1", "src", EvidenceType.METADATA, detected=False),
        create_evidence("2", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    structure_findings = [f for f in findings if f.rule_id == "STRUCT-001"]
    assert len(structure_findings) == 1
    finding = structure_findings[0]
    assert finding.category == FindingCategory.STRUCTURE
    assert finding.severity == FindingSeverity.MEDIUM
    assert "source" in finding.title.lower()
    assert finding.evidence_ids == ["ev-1"]


def test_source_files_exist_no_struct_001():
    """Test that existing source files do not generate STRUCT-001."""
    profile = create_basic_profile(source_count=5)  # Has source files
    evidence = [
        create_evidence("1", "src", EvidenceType.STRUCTURE, detected=True),
        create_evidence("2", "README.md", EvidenceType.FILE_CONTENT, detected=True),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    structure_findings = [f for f in findings if f.rule_id == "STRUCT-001"]
    assert len(structure_findings) == 0


def test_multiple_findings_generated_together():
    """Test that multiple missing items generate multiple findings."""
    profile = create_basic_profile(
        source_count=0,  # No source files
        test_count=0,    # No test files
    )
    evidence = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", "Dockerfile", EvidenceType.METADATA, detected=False),
        create_evidence("3", "requirements.txt", EvidenceType.METADATA, detected=False),
        create_evidence("4", "src", EvidenceType.METADATA, detected=False),
        create_evidence("5", "tests", EvidenceType.METADATA, detected=False),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    # Should have findings for all missing items
    rule_ids = {f.rule_id for f in findings}
    expected_rules = {"DOC-001", "TEST-001", "CONT-001", "DEP-001", "STRUCT-001"}
    assert rule_ids == expected_rules
    assert len(findings) == 5


def test_findings_contain_valid_evidence_references():
    """Test that findings reference valid evidence IDs."""
    profile = create_basic_profile(source_count=0, test_count=0)
    evidence = [
        create_evidence("readme-ev", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("docker-ev", "Dockerfile", EvidenceType.METADATA, detected=False),
        create_evidence("dep-ev", "requirements.txt", EvidenceType.METADATA, detected=False),
        create_evidence("src-ev", "src", EvidenceType.METADATA, detected=False),
        create_evidence("test-ev", "tests", EvidenceType.METADATA, detected=False),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    # Collect all evidence IDs referenced in findings
    referenced_evidence_ids = set()
    for finding in findings:
        referenced_evidence_ids.update(finding.evidence_ids)

    # All referenced IDs should exist in the evidence list
    evidence_ids = {ev.id for ev in evidence}
    assert referenced_evidence_ids.issubset(evidence_ids)


def test_finding_ids_are_stable():
    """Test that finding IDs are stable (deterministic)."""
    profile = create_basic_profile()
    evidence = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", "Dockerfile", EvidenceType.METADATA, detected=False),
        create_evidence("3", "requirements.txt", EvidenceType.METADATA, detected=False),
    ]

    analyzer = RepositoryAnalyzer()

    # Run analysis multiple times
    findings1 = analyzer.analyze(profile, evidence)
    findings2 = analyzer.analyze(profile, evidence)
    findings3 = analyzer.analyze(profile, evidence)

    # IDs should be the same across runs
    assert len(findings1) == len(findings2) == len(findings3) == 3

    # Sort findings by rule_id to ensure consistent comparison
    findings1_sorted = sorted(findings1, key=lambda f: f.rule_id)
    findings2_sorted = sorted(findings2, key=lambda f: f.rule_id)
    findings3_sorted = sorted(findings3, key=lambda f: f.rule_id)

    # Check that corresponding findings have the same ID across runs
    for f1, f2, f3 in zip(findings1_sorted, findings2_sorted, findings3_sorted):
        assert f1.rule_id == f2.rule_id == f3.rule_id
        assert f1.id == f2.id == f3.id


def test_analyzer_is_deterministic():
    """Test that analyzer produces same output for same input."""
    profile1 = create_basic_profile(file_count=10, source_count=5, test_count=0)
    profile2 = create_basic_profile(file_count=10, source_count=5, test_count=0)

    evidence1 = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", "tests", EvidenceType.METADATA, detected=False),
    ]
    evidence2 = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", "tests", EvidenceType.METADATA, detected=False),
    ]

    analyzer = RepositoryAnalyzer()
    findings1 = analyzer.analyze(profile1, evidence1)
    findings2 = analyzer.analyze(profile2, evidence2)

    # Should produce identical findings
    assert len(findings1) == len(findings2)
    for f1, f2 in zip(findings1, findings2):
        assert f1.rule_id == f2.rule_id
        assert f1.category == f2.category
        assert f1.severity == f2.severity
        assert f1.title == f2.title
        assert f1.description == f2.description
        assert f1.evidence_ids == f2.evidence_ids


def test_empty_repository_handled_correctly():
    """Test that empty repository is handled correctly."""
    profile = RepositoryProfile(
        name="empty-repo",
        file_count=0,
        metadata={
            "source_file_count": 0,
            "test_file_count": 0,
            "total_directories": 0,
        }
    )
    evidence = [
        create_evidence("1", "README.md", EvidenceType.METADATA, detected=False),
        create_evidence("2", "Dockerfile", EvidenceType.METADATA, detected=False),
        create_evidence("3", "requirements.txt", EvidenceType.METADATA, detected=False),
        create_evidence("4", "src", EvidenceType.METADATA, detected=False),
        create_evidence("5", "tests", EvidenceType.METADATA, detected=False),
    ]

    analyzer = RepositoryAnalyzer()
    findings = analyzer.analyze(profile, evidence)

    # Should generate findings for all missing items
    assert len(findings) == 5
    rule_ids = {f.rule_id for f in findings}
    expected_rules = {"DOC-001", "TEST-001", "CONT-001", "DEP-001", "STRUCT-001"}
    assert rule_ids == expected_rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])