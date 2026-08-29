"""LLM provider abstraction for Repository Quality Auditor."""

from typing import List, Protocol, runtime_checkable
from auditor.models.models import RepositoryProfile, Evidence, Finding
from auditor.models.scan_result import QualityScore
from auditor.models.llm_insight import LLMInsight


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers that generate insights from audit data."""

    def generate_insights(
        self,
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> LLMInsight:
        """
        Generate insights from audit data.

        Args:
            repository_profile: Profile of the scanned repository
            evidence: List of evidence collected during scan
            findings: List of findings generated from analysis
            quality_score: Calculated quality score from findings

        Returns:
            LLMInsight object containing explanations and recommendations

        Raises:
            LLMProviderError: If there's an error generating insights
        """
        ...


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMApiKeyError(LLMProviderError):
    """Raised when API key is missing or invalid."""
    pass


class LLMResponseError(LLMProviderError):
    """Raised when LLM returns invalid or unexpected response."""
    pass