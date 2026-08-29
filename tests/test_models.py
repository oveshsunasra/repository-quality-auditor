"""Unit tests for data models."""

import pytest
from datetime import datetime
from auditor.models.models import (
    RepositoryProfile,
    Evidence,
    EvidenceType,
    Finding,
    SeverityLevel,
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
        title="Hardcoded secret",
        description="Found hardcoded API key in source code",
        severity=SeverityLevel.HIGH,
        category="security",
        evidence_ids=["ev-1"],
        file_path="config.py",
        line_number=42,
        confidence=0.95
    )

    assert finding.id == "finding-1"
    assert finding.title == "Hardcoded secret"
    assert finding.description == "Found hardcoded API key in source code"
    assert finding.severity == SeverityLevel.HIGH
    assert finding.category == "security"
    assert finding.evidence_ids == ["ev-1"]
    assert finding.file_path == "config.py"
    assert finding.line_number == 42
    assert finding.confidence == 0.95


def test_audit_report_creation():
    """Test creating an AuditReport."""
    profile = RepositoryProfile(name="test-repo")
    evidence = Evidence(
        id="ev-1",
        type=EvidenceType.METADATA,
        source="README.md",
        content="# Test Repo"
    )
    finding = Finding(
        id="finding-1",
        title="Missing license",
        description="No license file found",
        severity=SeverityLevel.MEDIUM,
        category="legal",
        evidence_ids=["ev-1"]
    )

    report = AuditReport(
        repository_profile=profile,
        evidence=[evidence],
        findings=[finding],
        total_evidence_count=1,
        total_findings_count=1
    )

    assert report.repository_profile.name == "test-repo"
    assert len(report.evidence) == 1
    assert len(report.findings) == 1
    assert report.total_evidence_count == 1
    assert report.total_findings_count == 1
    assert isinstance(report.audit_started_at, datetime)


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