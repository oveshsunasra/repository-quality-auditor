"""LLM service for orchestrating insight generation."""

from typing import List, Optional
from auditor.llm.base import LLMProvider, LLMProviderError
from auditor.models.models import RepositoryProfile, Evidence, Finding
from auditor.models.scan_result import QualityScore
from auditor.models.llm_insight import LLMInsight
from auditor.llm.prompt_builder import build_llm_prompt
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating LLM insights from audit data."""

    def __init__(self, provider: LLMProvider):
        """
        Initialize LLM service.

        Args:
            provider: LLM provider to use for insight generation
        """
        self.provider = provider

    def generate_insights(
        self,
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> Optional[LLMInsight]:
        """
        Generate insights from audit data.

        Args:
            repository_profile: Profile of the scanned repository
            evidence: List of evidence collected during scan
            findings: List of findings generated from analysis
            quality_score: Calculated quality score from findings

        Returns:
            LLMInsight object if successful, None if insights cannot be generated
        """
        try:
            # Generate insights using the provider
            insight = self.provider.generate_insights(
                repository_profile, evidence, findings, quality_score
            )

            logger.info("Successfully generated LLM insights")
            return insight

        except Exception as e:
            # Log the error but don't crash - return None for graceful degradation
            logger.warning(f"Failed to generate LLM insights: {e}")
            return None


def create_llm_service() -> Optional[LLMService]:
    """
    Create an LLM service if configuration is available.

    Returns:
        LLMService instance if OpenAI API key is available, None otherwise
    """
    import os

    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.info("OpenAI API key not found - LLM insights disabled")
        return None

    try:
        # Create OpenAI provider
        from auditor.llm.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key=api_key)

        # Create and return service
        service = LLMService(provider)
        logger.info("LLM service initialized successfully")
        return service

    except Exception as e:
        logger.warning(f"Failed to initialize LLM service: {e}")
        return None