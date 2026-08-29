"""Deterministic quality scoring engine for Repository Quality Auditor."""

from typing import List
from auditor.models.models import Finding
from auditor.models.quality_score import QualityScore


class QualityScorer:
    """Calculates deterministic quality scores from audit findings."""

    # Severity-based deduction values
    SEVERITY_DEDUCTIONS = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
        "info": 0
    }

    def score(self, findings: List[Finding]) -> QualityScore:
        """
        Calculate quality score from a list of findings.

        Args:
            findings: List of Finding objects from repository analysis

        Returns:
            QualityScore object containing calculated score and deductions
        """
        if not findings:
            return QualityScore(
                score=100,
                max_score=100,
                grade="A",
                deductions=[],
                finding_count=0
            )

        # Calculate deductions based on severity
        deductions = []
        total_deduction = 0

        for finding in findings:
            severity_key = finding.severity.value.lower()
            points = self.SEVERITY_DEDUCTIONS.get(severity_key, 0)

            if points > 0:  # Only add deductions for non-zero point severities
                deduction_record = {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity.value,
                    "points": points
                }
                deductions.append(deduction_record)
                total_deduction += points

        # Calculate final score (never negative)
        score = max(0, 100 - total_deduction)

        # Calculate grade based on score
        grade = self._calculate_grade(score)

        # Sort deductions deterministically: by severity priority, then rule_id
        deductions.sort(key=lambda d: (
            self._severity_priority(d["severity"]),
            d["rule_id"]
        ))

        return QualityScore(
            score=score,
            max_score=100,
            grade=grade,
            deductions=deductions,
            finding_count=len(findings)
        )

    def _severity_priority(self, severity: str) -> int:
        """Convert severity to numeric priority for sorting (lower = higher priority)."""
        priority_map = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4
        }
        return priority_map.get(severity.lower(), 5)

    def _calculate_grade(self, score: int) -> str:
        """Calculate letter grade based on score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"