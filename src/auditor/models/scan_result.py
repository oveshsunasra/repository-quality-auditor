"""Scan result model for Repository Quality Auditor."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, computed_field

from auditor.models.models import (
    RepositoryProfile,
    Evidence,
)


class ScanResult(BaseModel):
    """Result of a repository scan."""
    repository_profile: RepositoryProfile = Field(description="Profile of the scanned repository")
    evidence: List[Evidence] = Field(default_factory=list, description="Collected evidence during scan")
    scan_completed_at: datetime = Field(default_factory=datetime.now, description="When scan completed")
    scanner_version: str = Field(default="0.1.0", description="Version of the scanner used")

    @computed_field
    @property
    def total_evidence_count(self) -> int:
        """Total number of evidence items collected."""
        return len(self.evidence)

    @computed_field
    @property
    def total_findings_count(self) -> int:
        """Total number of findings (0 for scanner as it doesn't produce findings yet)."""
        return 0  # Scanner doesn't produce findings - that's for later analyzers/agents