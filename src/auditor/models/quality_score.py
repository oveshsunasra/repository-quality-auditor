"""Pydantic model for repository quality score."""

from typing import List, Optional
from pydantic import BaseModel, Field, computed_field
from auditor.models.models import Finding


class QualityScore(BaseModel):
    """Calculated quality score for a repository audit."""

    score: int = Field(description="Calculated quality score (0-100)")
    max_score: int = Field(default=100, description="Maximum possible score")
    grade: str = Field(description="Letter grade based on score")
    deductions: List[dict] = Field(default_factory=list, description="List of deductions explaining score calculation")
    finding_count: int = Field(description="Number of findings that contributed to the score")

    @computed_field
    @property
    def is_passing(self) -> bool:
        """Whether the score is considered passing (grade C or better)."""
        return self.score >= 70