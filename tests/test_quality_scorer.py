"""Unit tests for quality scorer."""

import pytest
from auditor.models.models import (
    Finding,
    FindingSeverity,
    FindingCategory,
)
from auditor.models.quality_score import QualityScore
from auditor.analyzers.repository_analyzer import RepositoryAnalyzer
from auditor.scoring.quality_scorer import QualityScorer


def create_finding(rule_id, severity, category=FindingCategory.TESTING, title="Test finding", description="Test description"):
    """Create a finding for testing."""
    return Finding(
        id=f"test-{rule_id}",
        rule_id=rule_id,
        title=title,
        description=description,
        severity=severity,
        category=category,
        evidence_ids=["test-evidence"]
    )


def test_no_findings():
    """Test that no findings results in perfect score."""
    scorer = QualityScorer()
    score = scorer.score([])

    assert isinstance(score, QualityScore)
    assert score.score == 100
    assert score.max_score == 100
    assert score.grade == "A"
    assert score.deductions == []
    assert score.finding_count == 0
    assert score.is_passing is True


def test_one_low_finding():
    """Test score with one LOW finding."""
    finding = create_finding("LOW-001", FindingSeverity.LOW)
    scorer = QualityScorer()
    score = scorer.score([finding])

    assert score.score == 97  # 100 - 3
    assert score.grade == "A"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "LOW-001"
    assert score.deductions[0]["severity"] == "low"
    assert score.deductions[0]["points"] == 3
    assert score.finding_count == 1


def test_one_medium_finding():
    """Test score with one MEDIUM finding."""
    finding = create_finding("MED-001", FindingSeverity.MEDIUM)
    scorer = QualityScorer()
    score = scorer.score([finding])

    assert score.score == 92  # 100 - 8
    assert score.grade == "A"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "MED-001"
    assert score.deductions[0]["severity"] == "medium"
    assert score.deductions[0]["points"] == 8
    assert score.finding_count == 1


def test_one_high_finding():
    """Test score with one HIGH finding."""
    finding = create_finding("HIGH-001", FindingSeverity.HIGH)
    scorer = QualityScorer()
    score = scorer.score([finding])

    assert score.score == 85  # 100 - 15
    assert score.grade == "B"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "HIGH-001"
    assert score.deductions[0]["severity"] == "high"
    assert score.deductions[0]["points"] == 15
    assert score.finding_count == 1


def test_one_critical_finding():
    """Test score with one CRITICAL finding."""
    finding = create_finding("CRIT-001", FindingSeverity.CRITICAL)
    scorer = QualityScorer()
    score = scorer.score([finding])

    assert score.score == 75  # 100 - 25
    assert score.grade == "C"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "CRIT-001"
    assert score.deductions[0]["severity"] == "critical"
    assert score.deductions[0]["points"] == 25
    assert score.finding_count == 1


def test_multiple_findings():
    """Test score with multiple findings."""
    findings = [
        create_finding("HIGH-001", FindingSeverity.HIGH),
        create_finding("MED-001", FindingSeverity.MEDIUM),
        create_finding("LOW-001", FindingSeverity.LOW),
        create_finding("CRIT-001", FindingSeverity.CRITICAL),
    ]
    scorer = QualityScorer()
    score = scorer.score(findings)

    # Total deduction: 15 + 8 + 3 + 25 = 51
    assert score.score == 49  # 100 - 51
    assert score.grade == "F"
    assert len(score.deductions) == 4
    assert score.finding_count == 4


def test_score_never_negative():
    """Test that score never goes below zero even with many findings."""
    # Create enough findings to exceed 100 points deduction
    findings = [
        create_finding(f"CRIT-{i}", FindingSeverity.CRITICAL) for i in range(5)  # 5 * 25 = 125 points
    ]
    scorer = QualityScorer()
    score = scorer.score(findings)

    assert score.score == 0  # Should be capped at 0
    assert score.grade == "F"
    assert len(score.deductions) == 5
    assert score.finding_count == 5


def test_grade_boundaries():
    """Test grade calculation at boundary scores."""
    scorer = QualityScorer()

    # Test exact boundaries
    test_cases = [
        (100, "A"),
        (99, "A"),
        (90, "A"),
        (89, "B"),
        (88, "B"),
        (80, "B"),
        (79, "C"),
        (78, "C"),
        (70, "C"),
        (69, "D"),
        (68, "D"),
        (60, "D"),
        (59, "F"),
        (58, "F"),
        (0, "F"),
    ]

    for score, expected_grade in test_cases:
        # We need to create findings that result in this exact score
        # For simplicity, we'll test the grade calculation directly
        grade = scorer._calculate_grade(score)
        assert grade == expected_grade, f"Score {score} should give grade {expected_grade}, got {grade}"


def test_deduction_ordering():
    """Test that deductions are ordered deterministically."""
    findings = [
        create_finding("Z-RULE", FindingSeverity.LOW),      # low = 3 points
        create_finding("A-RULE", FindingSeverity.HIGH),     # high = 15 points
        create_finding("M-RULE", FindingSeverity.MEDIUM),   # medium = 8 points
        create_finding("B-RULE", FindingSeverity.HIGH),     # high = 15 points
    ]
    scorer = QualityScorer()
    score = scorer.score(findings)

    # Should be ordered by severity priority (high first, then medium, then low)
    # Within same severity, ordered by rule_id
    expected_order = ["A-RULE", "B-RULE", "M-RULE", "Z-RULE"]
    actual_order = [d["rule_id"] for d in score.deductions]

    assert actual_order == expected_order
    assert score.deductions[0]["severity"] == "high"
    assert score.deductions[1]["severity"] == "high"
    assert score.deductions[2]["severity"] == "medium"
    assert score.deductions[3]["severity"] == "low"


def test_same_findings_produce_same_score():
    """Test that identical findings always produce identical scores."""
    findings1 = [
        create_finding("TEST-001", FindingSeverity.HIGH),
        create_finding("TEST-002", FindingSeverity.MEDIUM),
        create_finding("TEST-003", FindingSeverity.LOW),
    ]
    findings2 = [
        create_finding("TEST-001", FindingSeverity.HIGH),
        create_finding("TEST-002", FindingSeverity.MEDIUM),
        create_finding("TEST-003", FindingSeverity.LOW),
    ]
    findings3 = [
        create_finding("TEST-003", FindingSeverity.LOW),
        create_finding("TEST-001", FindingSeverity.HIGH),
        create_finding("TEST-002", FindingSeverity.MEDIUM),
    ]

    scorer = QualityScorer()
    score1 = scorer.score(findings1)
    score2 = scorer.score(findings2)
    score3 = scorer.score(findings3)

    assert score1.score == score2.score == score3.score
    assert score1.grade == score2.grade == score3.grade
    assert len(score1.deductions) == len(score2.deductions) == len(score3.deductions)
    # Deductions should be in same order due to deterministic sorting
    assert score1.deductions == score2.deductions == score3.deductions


def test_info_findings_no_deduction():
    """Test that INFO findings don't affect score."""
    findings = [
        create_finding("INFO-001", FindingSeverity.INFO),
        create_finding("INFO-002", FindingSeverity.INFO),
    ]
    scorer = QualityScorer()
    score = scorer.score(findings)

    assert score.score == 100  # No deduction for INFO
    assert score.grade == "A"
    assert len(score.deductions) == 0  # INFO findings should not create deductions
    assert score.finding_count == 2


def test_empty_findings_list():
    """Test scoring with explicitly empty list."""
    scorer = QualityScorer()
    score = scorer.score([])

    assert score.score == 100
    assert score.grade == "A"
    assert score.deductions == []
    assert score.finding_count == 0


def test_integration_with_analyzer():
    """Test that quality scorer works with repository analyzer output."""
    # This test would require mocking scanner output, but we can test the concept
    scorer = QualityScorer()
    analyzer = RepositoryAnalyzer()

    # Create some sample findings similar to what analyzer would produce
    findings = [
        Finding(
            id="doc-001",
            rule_id="DOC-001",
            title="README file is missing",
            description="No recognized README file was detected in the repository.",
            severity=FindingSeverity.MEDIUM,
            category=FindingCategory.DOCUMENTATION,
            evidence_ids=["ev-readme-missing"]
        ),
        Finding(
            id="test-001",
            rule_id="TEST-001",
            title="No test files detected",
            description="No test files were detected in the repository.",
            severity=FindingSeverity.HIGH,
            category=FindingCategory.TESTING,
            evidence_ids=["ev-test-missing"]
        )
    ]

    score = scorer.score(findings)

    assert score.score == 77  # 100 - 8 (MEDIUM) - 15 (HIGH) = 77
    assert score.grade == "C"
    assert len(score.deductions) == 2
    assert score.finding_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])