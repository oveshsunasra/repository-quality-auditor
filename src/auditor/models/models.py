"""Pydantic models for repository quality auditor."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, computed_field


class EvidenceType(str, Enum):
    """Types of evidence that can be collected during analysis."""
    FILE_CONTENT = "file_content"
    METADATA = "metadata"
    STRUCTURE = "structure"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"


class SeverityLevel(str, Enum):
    """Severity levels for findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingSeverity(str, Enum):
    """Severity levels for audit findings."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(str, Enum):
    """Categories for audit findings."""
    STRUCTURE = "structure"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPENDENCY = "dependency"
    CONTAINERIZATION = "containerization"


class RepositoryProfile(BaseModel):
    """Profile of a repository being audited."""
    name: str = Field(description="Repository name")
    url: Optional[str] = Field(default=None, description="Repository URL")
    description: Optional[str] = Field(default=None, description="Repository description")
    language: Optional[str] = Field(default=None, description="Primary programming language")
    stars: Optional[int] = Field(default=None, description="Number of stars (if applicable)")
    size_kb: Optional[int] = Field(default=None, description="Repository size in kilobytes")
    file_count: Optional[int] = Field(default=None, description="Number of files")
    created_at: Optional[datetime] = Field(default=None, description="Repository creation date")
    updated_at: Optional[datetime] = Field(default=None, description="Last update date")
    topics: List[str] = Field(default_factory=list, description="Repository topics/tags")
    license: Optional[str] = Field(default=None, description="Repository license")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Evidence(BaseModel):
    """Piece of evidence collected during analysis."""
    id: str = Field(description="Unique identifier for the evidence")
    type: EvidenceType = Field(description="Type of evidence")
    source: str = Field(description="Source of evidence (e.g., file path, command output)")
    content: str = Field(description="Evidence content")
    collected_at: datetime = Field(default_factory=datetime.now, description="When evidence was collected")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Finding(BaseModel):
    """Finding discovered during analysis."""
    id: str = Field(description="Unique identifier for the finding")
    rule_id: str = Field(description="Unique identifier for the rule that generated this finding")
    title: str = Field(description="Short title of the finding")
    description: str = Field(description="Detailed description of the finding")
    severity: FindingSeverity = Field(description="Severity level of the finding")
    category: FindingCategory = Field(description="Category of finding")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence supporting this finding")
    file_path: Optional[str] = Field(default=None, description="File path related to the finding (if applicable)")
    line_number: Optional[int] = Field(default=None, description="Line number related to the finding (if applicable)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the finding (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AuditReport(BaseModel):
    """Complete audit report for a repository."""
    repository_profile: RepositoryProfile = Field(description="Profile of the audited repository")
    evidence: List[Evidence] = Field(default_factory=list, description="Collected evidence")
    findings: List[Finding] = Field(default_factory=list, description="Discovered findings")
    audit_started_at: datetime = Field(default_factory=datetime.now, description="When audit started")
    audit_completed_at: Optional[datetime] = Field(default=None, description="When audit completed")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @computed_field
    @property
    def total_evidence_count(self) -> int:
        """Total number of evidence items."""
        return len(self.evidence)

    @computed_field
    @property
    def total_findings_count(self) -> int:
        """Total number of findings."""
        return len(self.findings)