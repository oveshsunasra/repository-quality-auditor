"""Prompt builder for LLM insight generation."""

from typing import List, Dict, Any
from auditor.models.models import RepositoryProfile, Evidence, Finding
from auditor.models.scan_result import QualityScore


class LLMPromptBuilder:
    """Builds prompts for LLM insight generation from audit data."""

    def __init__(self):
        """Initialize prompt builder."""
        pass

    def build_prompt(
        self,
        repository_profile: RepositoryProfile,
        evidence: List[Evidence],
        findings: List[Finding],
        quality_score: QualityScore,
    ) -> str:
        """
        Build a prompt for LLM insight generation.

        Args:
            repository_profile: Profile of the scanned repository
            evidence: List of evidence collected during scan
            findings: List of findings generated from analysis
            quality_score: Calculated quality score from findings

        Returns:
            Formatted prompt string
        """
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


# Convenience function
def build_llm_prompt(
    repository_profile: RepositoryProfile,
    evidence: List[Evidence],
    findings: List[Finding],
    quality_score: QualityScore,
) -> str:
    """
    Build a prompt for LLM insight generation.

    Args:
        repository_profile: Profile of the scanned repository
        evidence: List of evidence collected during scan
        findings: List of findings generated from analysis
        quality_score: Calculated quality score from findings

    Returns:
        Formatted prompt string
    """
    builder = LLMPromptBuilder()
    return builder.build_prompt(repository_profile, evidence, findings, quality_score)