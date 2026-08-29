"""LLM-generated insights model for Repository Quality Auditor."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExplanationItem(BaseModel):
    """An explanation linked to a specific finding rule."""
    rule_id: str = Field(description="The rule ID this explanation relates to")
    explanation: str = Field(description="Explanation of the finding")


class RecommendationItem(BaseModel):
    """A recommendation linked to a specific finding rule."""
    rule_id: str = Field(description="The rule ID this recommendation relates to")
    recommendation: str = Field(description="Actionable recommendation")


class LLMRiskFactor(BaseModel):
    """A risk factor identified by the LLM."""
    description: str = Field(description="Description of the risk")
    severity: str = Field(description="Severity of the risk (low, medium, high, critical)")


class LLMModelMetadata(BaseModel):
    """Metadata about the LLM model used."""
    model_name: str = Field(description="Name of the LLM model used")
    provider: str = Field(description="LLM provider (e.g., openai)")
    timestamp: datetime = Field(description="When the insight was generated")
    token_usage: Optional[Dict[str, int]] = Field(
        default=None,
        description="Token usage statistics if available"
    )


class LLMInsight(BaseModel):
    """LLM-generated insights for repository audit."""
    summary: str = Field(description="High-level summary of the repository audit")
    explanations: List[ExplanationItem] = Field(
        default_factory=list,
        description="Explanations of findings, linked to rule IDs"
    )
    recommendations: List[RecommendationItem] = Field(
        default_factory=list,
        description="Actionable recommendations, linked to rule IDs"
    )
    risks: List[LLMRiskFactor] = Field(
        default_factory=list,
        description="Risk factors identified by the LLM"
    )
    model_metadata: LLMModelMetadata = Field(
        description="Metadata about the LLM model used"
    )