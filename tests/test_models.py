"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from auditor.models.models import (
    RepositoryProfile,
    Evidence,
    EvidenceType,
    Finding,
    SeverityLevel,
    FindingSeverity,
    FindingCategory,
    AuditReport
)


def test_repository_profile_creation():
    """Test creating a RepositoryProfile."""
    profile = RepositoryProfile(
        name="test-repo",
        description="A test repository",
        language="Python",
        stars=100
    )

    assert profile.name == "test-repo"
    assert profile.description == "A test repository"
    assert profile.language == "Python"
    assert profile.stars == 100
    assert isinstance(profile.created_at, datetime) or profile.created_at is None


def test_evidence_creation():
    """Test creating Evidence."""
    evidence = Evidence(
        id="ev-1",
        type=EvidenceType.FILE_CONTENT,
        source="test.py",
        content="print('hello world')"
    )

    assert evidence.id == "ev-1"
    assert evidence.type == EvidenceType.FILE_CONTENT
    assert evidence.source == "test.py"
    assert evidence.content == "print('hello world')"
    assert isinstance(evidence.collected_at, datetime)


def test_finding_creation():
    """Test creating a Finding."""
    finding = Finding(
        id="finding-1",
        rule_id="TEST-001",
        title="Hardcoded secret",
        description="Found hardcoded API key in source code",
        severity=FindingSeverity.HIGH,
        category=FindingCategory.TESTING,  # Using TESTING as closest to "security" for test
        evidence_ids=["ev-1"],
        file_path="config.py",
        line_number=42,
        confidence=0.95
    )

    assert finding.id == "finding-1"
    assert finding.rule_id == "TEST-001"
    assert finding.title == "Hardcoded secret"
    assert finding.description == "Found hardcoded API key in source code"
    assert finding.severity == FindingSeverity.HIGH
    assert finding.category == FindingCategory.TESTING
    assert finding.evidence_ids == ["ev-1"]
    assert finding.file_path == "config.py"
    assert finding.line_number == 42
    assert finding.confidence == 0.95


def test_audit_report_creation():
    """Test creating an AuditReport with derived counts."""
    profile = RepositoryProfile(name="test-repo")
    evidence = Evidence(
        id="ev-1",
        type=EvidenceType.METADATA,
        source="README.md",
        content="# Test Repo"
    )
    finding = Finding(
        id="finding-1",
        rule_id="STRUCT-001",
        title="Missing license",
        description="No license file found",
        severity=FindingSeverity.MEDIUM,
        category=FindingCategory.STRUCTURE,  # Using STRUCTURE as closest to "legal" for test
        evidence_ids=["ev-1"]
    )

    report = AuditReport(
        repository_profile=profile,
        evidence=[evidence],
        findings=[finding]
    )

    assert report.repository_profile.name == "test-repo"
    assert len(report.evidence) == 1
    assert len(report.findings) == 1
    assert report.total_evidence_count == 1  # Derived from evidence list
    assert report.total_findings_count == 1  # Derived from findings list
    assert isinstance(report.audit_started_at, datetime)


def test_audit_report_empty_lists():
    """Test AuditReport with empty evidence and findings lists."""
    profile = RepositoryProfile(name="empty-repo")

    report = AuditReport(
        repository_profile=profile,
        evidence=[],
        findings=[]
    )

    assert report.repository_profile.name == "empty-repo"
    assert len(report.evidence) == 0
    assert len(report.findings) == 0
    assert report.total_evidence_count == 0  # Derived from evidence list
    assert report.total_findings_count == 0  # Derived from findings list


def test_audit_report_multiple_items():
    """Test AuditReport with multiple evidence and findings."""
    profile = RepositoryProfile(name="multi-repo")

    evidence1 = Evidence(
        id="ev-1",
        type=EvidenceType.FILE_CONTENT,
        source="file1.py",
        content="content1"
    )
    evidence2 = Evidence(
        id="ev-2",
        type=EvidenceType.METADATA,
        source="README.md",
        content="# Test"
    )

    finding1 = Finding(
        id="f-1",
        rule_id="TEST-001",
        title="Finding 1",
        description="First finding",
        severity=FindingSeverity.LOW,
        category=FindingCategory.TESTING,
        evidence_ids=["ev-1"]
    )
    finding2 = Finding(
        id="f-2",
        rule_id="TEST-002",
        title="Finding 2",
        description="Second finding",
        severity=FindingSeverity.HIGH,
        category=FindingCategory.TESTING,
        evidence_ids=["ev-2"]
    )

    report = AuditReport(
        repository_profile=profile,
        evidence=[evidence1, evidence2],
        findings=[finding1, finding2]
    )

    assert len(report.evidence) == 2
    assert len(report.findings) == 2
    assert report.total_evidence_count == 2  # Derived from evidence list
    assert report.total_findings_count == 2  # Derived from findings list


def test_finding_confidence_boundaries():
    """Test Finding confidence field boundaries."""
    # Valid boundaries
    finding_min = Finding(
        id="f-min",
        rule_id="TEST-001",
        title="Min confidence",
        description="Test",
        severity=FindingSeverity.LOW,
        category=FindingCategory.TESTING,
        confidence=0.0
    )
    assert finding_min.confidence == 0.0

    finding_max = Finding(
        id="f-max",
        rule_id="TEST-001",
        title="Max confidence",
        description="Test",
        severity=FindingSeverity.LOW,
        category=FindingCategory.TESTING,
        confidence=1.0
    )
    assert finding_max.confidence == 1.0

    # Invalid values should raise ValidationError
    with pytest.raises(ValidationError):
        Finding(
            id="f-invalid-low",
            rule_id="TEST-001",
            title="Invalid low",
            description="Test",
            severity=FindingSeverity.LOW,
            category=FindingCategory.TESTING,
            confidence=-0.1
        )

    with pytest.raises(ValidationError):
        Finding(
            id="f-invalid-high",
            rule_id="TEST-001",
            title="Invalid high",
            description="Test",
            severity=FindingSeverity.LOW,
            category=FindingCategory.TESTING,
            confidence=1.1
        )


def test_optional_fields_none():
    """Test that optional fields accept None values."""
    profile = RepositoryProfile(
        name="none-test",
        url=None,
        description=None,
        language=None,
        stars=None,
        size_kb=None,
        file_count=None,
        created_at=None,
        updated_at=None,
        topics=[],  # Empty list is fine
        license=None,
        metadata={}  # Empty dict is fine
    )

    assert profile.url is None
    assert profile.description is None
    assert profile.language is None
    assert profile.stars is None
    assert profile.size_kb is None
    assert profile.file_count is None
    assert profile.created_at is None
    assert profile.updated_at is None
    assert profile.license is None
    assert profile.metadata == {}


def test_evidence_optional_metadata():
    """Test Evidence with optional metadata."""
    evidence = Evidence(
        id="ev-none-meta",
        type=EvidenceType.FILE_CONTENT,
        source="test.py",
        content="print('hello')",
        metadata={}  # Empty metadata
    )

    assert evidence.metadata == {}


def test_finding_optional_fields():
    """Test Finding with optional fields."""
    finding = Finding(
        id="f-none-opt",
        rule_id="TEST-001",
        title="Optional fields test",
        description="Test optional fields",
        severity=FindingSeverity.INFO,
        category=FindingCategory.TESTING,
        evidence_ids=[],  # Empty list
        file_path=None,   # None value
        line_number=None, # None value
        confidence=0.5,
        metadata={}       # Empty metadata
    )

    assert finding.evidence_ids == []
    assert finding.file_path is None
    assert finding.line_number is None
    assert finding.metadata == {}


def test_evidence_type_enum():
    """Test EvidenceType enum."""
    assert EvidenceType.FILE_CONTENT == "file_content"
    assert EvidenceType.METADATA == "metadata"
    assert EvidenceType.STRUCTURE == "structure"


def test_severity_level_enum():
    """Test SeverityLevel enum."""
    assert SeverityLevel.INFO == "info"
    assert SeverityLevel.LOW == "low"
    assert SeverityLevel.MEDIUM == "medium"
    assert SeverityLevel.HIGH == "high"
    assert SeverityLevel.CRITICAL == "critical"