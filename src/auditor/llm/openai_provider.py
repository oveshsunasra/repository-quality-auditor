"""OpenAI LLM provider for Repository Quality Auditor."""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai import APITimeoutError, APIConnectionError, RateLimitError, APIError, AuthenticationError

from auditor.llm.base import LLMProvider, LLMProviderError, LLMApiKeyError, LLMResponseError
from auditor.models.models import RepositoryProfile, Evidence, Finding
from auditor.models.scan_result import QualityScore
from auditor.models.llm_insight import LLMInsight, ExplanationItem, RecommendationItem, LLMRiskFactor, LLMModelMetadata


class OpenAIProviderError(LLMProviderError):
    """Raised when OpenAI provider encounters an error."""
    pass


class OpenAIProvider:
    """OpenAI-backed LLM provider for generating audit insights."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        timeout: Optional[float] = None
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to AUDITOR_LLM_MODEL env var or gpt-3.5-turbo)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds (defaults to AUDITOR_LLM_TIMEOUT env var or 30.0)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("AUDITOR_LLM_MODEL", "gpt-3.5-turbo")
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Parse timeout from environment or use default, with validation
        if timeout is not None:
            self.timeout = timeout
        else:
            timeout_env = os.getenv("AUDITOR_LLM_TIMEOUT", "30.0")
            try:
                self.timeout = float(timeout_env)
                if self.timeout <= 0:
                    raise ValueError("Timeout must be positive")
            except ValueError:
                # If invalid timeout in env, fall back to default
                self.timeout = 30.0

        if not self.api_key:
            raise LLMApiKeyError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )

    def generate_insights(
        self,
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> LLMInsight:
        """
        Generate insights from audit data using OpenAI.

        Args:
            repository_profile: Profile of the scanned repository
            evidence: List of evidence collected during scan
            findings: List of findings generated from analysis
            quality_score: Calculated quality score from findings

        Returns:
            LLMInsight object containing explanations and recommendations

        Raises:
            OpenAIProviderError: If there's an error generating insights
            LLMApiKeyError: If API key is missing or invalid
            LLMResponseError: If LLM returns invalid or unexpected response
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(repository_profile, evidence, findings, quality_score)

            # Call OpenAI API with timeout handling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}  # Request JSON output
            )

            # Parse and validate response
            content = response.choices[0].message.content
            if not content:
                raise LLMResponseError("Empty response from OpenAI API")

            # Parse JSON response
            import json
            try:
                response_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMResponseError(f"Invalid JSON response from OpenAI: {e}")

            # Convert to LLMInsight model
            insight = self._parse_response(response_data, repository_profile, evidence, findings, quality_score)

            # Add model metadata
            insight.model_metadata = LLMModelMetadata(
                model_name=self.model,
                provider="openai",
                timestamp=datetime.now(),
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                } if response.usage else None
            )

            return insight

        except APITimeoutError as e:
            raise OpenAIProviderError(f"OpenAI API request timed out after {self.timeout}s") from e
        except APIConnectionError as e:
            raise OpenAIProviderError(f"Failed to connect to OpenAI API: {e}") from e
        except RateLimitError as e:
            raise OpenAIProviderError(f"OpenAI API rate limit exceeded: {e}") from e
        except AuthenticationError as e:
            raise LLMApiKeyError(f"OpenAI authentication failed: {e}") from e
        except APIError as e:
            raise OpenAIProviderError(f"OpenAI API error: {e}") from e
        except Exception as e:
            if isinstance(e, (LLMApiKeyError, LLMResponseError)):
                raise
            raise OpenAIProviderError(f"Failed to generate insights: {e}") from e

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are an expert software engineer analyzing repository audit results.

Your role is to provide explanations and practical recommendations based on the authoritative audit data provided.
You must NOT:
- Invent facts not supported by the evidence
- Change finding severity levels
- Alter the quality score or grade
- Claim files exist unless supported by supplied evidence
- Make unsupported assertions about the repository

You MUST:
- Explain existing findings in clear, actionable terms
- Provide practical recommendations for improvement
- Reference rule IDs when explaining findings
- Focus on engineering-focused, actionable insights
- Acknowledge when evidence is insufficient to make claims"""

    def _build_prompt(
        self,
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> str:
        """Build the user prompt with audit context."""
        import json
        from datetime import datetime

        # Prepare structured context for the LLM
        context = {
            "repository_profile": {
                "name": repository_profile.name,
                "description": repository_profile.description,
                "language": repository_profile.language,
                "stars": repository_profile.stars,
                "size_kb": repository_profile.size_kb,
                "file_count": repository_profile.file_count,
                "topics": repository_profile.topics,
                "license": repository_profile.license,
                "metadata": repository_profile.metadata
            },
            "evidence_summary": {
                "total_count": len(evidence),
                "by_type": self._group_evidence_by_type(evidence),
                "key_detected": self._get_key_detected_items(evidence),
                "key_missing": self._get_key_missing_items(evidence)
            },
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "description": f.description,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "evidence_count": len(f.evidence_ids),
                    "confidence": f.confidence
                }
                for f in findings
            ],
            "quality_score": {
                "score": quality_score.score,
                "max_score": quality_score.max_score,
                "grade": quality_score.grade,
                "finding_count": quality_score.finding_count,
                "deductions": quality_score.deductions
            },
            "audit_timestamp": datetime.now().isoformat()
        }

        prompt = f"""Analyze this software repository audit and provide explanations and recommendations.

AUDIT CONTEXT:
{json.dumps(context, indent=2)}

INSTRUCTIONS:
1. Provide a high-level summary of the repository's current state
2. For each finding, explain what it means in practical terms
3. Provide actionable recommendations for addressing each finding
4. Identify any notable risk patterns or concerns
5. Keep explanations concise and engineering-focused
6. Make recommendations specific and implementable
7. Reference rule IDs when discussing specific findings
8. If evidence is insufficient for a claim, state that clearly

RESPONSE FORMAT:
Return a JSON object with exactly these fields:
{{
  "summary": "string - high-level summary of the repository audit",
  "explanations": [
    {{"rule_id": "string", "explanation": "string"}}
  ],
  "recommendations": [
    {{"rule_id": "string", "recommendation": "string"}}
  ],
  "risks": [
    {{"description": "string", "severity": "string (low|medium|high|critical)"}}
  ]
}}

Do not include any additional fields or text outside the JSON object."""

        return prompt

    def _group_evidence_by_type(self, evidence: List[Evidence]) -> Dict[str, int]:
        """Group evidence by type for summary."""
        groups = {}
        for ev in evidence:
            groups[ev.type.value] = groups.get(ev.type.value, 0) + 1
        return groups

    def _get_key_detected_items(self, evidence: List[Evidence]) -> List[str]:
        """Get list of key detected items from evidence."""
        detected = []
        for ev in evidence:
            if ev.metadata.get("detected", False) is True:
                detected.append(ev.source)
        return list(set(detected))  # Remove duplicates

    def _get_key_missing_items(self, evidence: List[Evidence]) -> List[str]:
        """Get list of key missing items from evidence."""
        missing = []
        for ev in evidence:
            if ev.metadata.get("detected", True) is False:
                missing.append(ev.source)
        return list(set(missing))  # Remove duplicates

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> LLMInsight:
        """Parse and validate OpenAI response into LLMInsight model."""
        # Validate required fields
        if "summary" not in response_data:
            raise LLMResponseError("Missing 'summary' field in LLM response")
        if "explanations" not in response_data:
            raise LLMResponseError("Missing 'explanations' field in LLM response")
        if "recommendations" not in response_data:
            raise LLMResponseError("Missing 'recommendations' field in LLM response")
        if "risks" not in response_data:
            raise LLMResponseError("Missing 'risks' field in LLM response")

        # Validate explanations
        explanations = []
        for exp in response_data["explanations"]:
            if not isinstance(exp, dict) or "rule_id" not in exp or "explanation" not in exp:
                raise LLMResponseError("Invalid explanation format in LLM response")
            explanations.append(ExplanationItem(
                rule_id=exp["rule_id"],
                explanation=str(exp["explanation"])
            ))

        # Validate recommendations
        recommendations = []
        for rec in response_data["recommendations"]:
            if not isinstance(rec, dict) or "rule_id" not in rec or "recommendation" not in rec:
                raise LLMResponseError("Invalid recommendation format in LLM response")
            recommendations.append(RecommendationItem(
                rule_id=rec["rule_id"],
                recommendation=str(rec["recommendation"])
            ))

        # Validate risks
        risks = []
        for risk in response_data["risks"]:
            if not isinstance(risk, dict) or "description" not in risk or "severity" not in risk:
                raise LLMResponseError("Invalid risk format in LLM response")
            risks.append(LLMRiskFactor(
                description=str(risk["description"]),
                severity=str(risk["severity"]).lower()
            ))

        return LLMInsight(
            summary=str(response_data["summary"]),
            explanations=explanations,
            recommendations=recommendations,
            risks=risks,
            model_metadata=LLMModelMetadata(  # Will be overwritten by caller
                model_name="",
                provider="",
                timestamp=datetime.now()
            )
        )


# Factory function for easy instantiation
def create_openai_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    **kwargs
) -> OpenAIProvider:
    """
    Create an OpenAI provider instance.

    Args:
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: Model name (defaults to AUDITOR_LLM_MODEL env var or gpt-3.5-turbo)
        timeout: Request timeout in seconds (defaults to AUDITOR_LLM_TIMEOUT env var or 30.0)
        **kwargs: Additional arguments passed to OpenAIProvider constructor

    Returns:
        OpenAIProvider instance
    """
    return OpenAIProvider(api_key=api_key, model=model, timeout=timeout, **kwargs)