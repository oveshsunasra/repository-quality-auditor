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


def test_empty_findings():
    """Test that no findings results in perfect score."""
    scorer = QualityScorer()
    score = scorer.score([])

    assert score.score == 100
    assert score.max_score == 100
    assert score.grade == "A"
    assert score.deductions == []
    assert score.finding_count == 0
    assert score.is_passing is True


def test_individual_severities():
    """Test score impact of individual severity findings."""
    scorer = QualityScorer()

    # LOW finding -> 97
    low_finding = create_finding("LOW-001", FindingSeverity.LOW)
    score = scorer.score([low_finding])
    assert score.score == 97  # 100 - 3
    assert score.grade == "A"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "LOW-001"
    assert score.deductions[0]["severity"] == "low"
    assert score.deductions[0]["points"] == 3

    # MEDIUM finding -> 92
    medium_finding = create_finding("MED-001", FindingSeverity.MEDIUM)
    score = scorer.score([medium_finding])
    assert score.score == 92  # 100 - 8
    assert score.grade == "A"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "MED-001"
    assert score.deductions[0]["severity"] == "medium"
    assert score.deductions[0]["points"] == 8

    # HIGH finding -> 85
    high_finding = create_finding("HIGH-001", FindingSeverity.HIGH)
    score = scorer.score([high_finding])
    assert score.score == 85  # 100 - 15
    assert score.grade == "B"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "HIGH-001"
    assert score.deductions[0]["severity"] == "high"
    assert score.deductions[0]["points"] == 15

    # CRITICAL finding -> 75
    critical_finding = create_finding("CRIT-001", FindingSeverity.CRITICAL)
    score = scorer.score([critical_finding])
    assert score.score == 75  # 100 - 25
    assert score.grade == "C"
    assert len(score.deductions) == 1
    assert score.deductions[0]["rule_id"] == "CRIT-001"
    assert score.deductions[0]["severity"] == "critical"
    assert score.deductions[0]["points"] == 25

    # INFO finding -> no deduction (100)
    info_finding = create_finding("INFO-001", FindingSeverity.INFO)
    score = scorer.score([info_finding])
    assert score.score == 100  # No deduction
    assert score.grade == "A"
    assert len(score.deductions) == 0  # INFO findings should not create deductions


def test_grade_boundaries_with_findings():
    """Test grade calculation at boundary scores using actual findings."""
    scorer = QualityScorer()

    # Score 100 -> A (no findings)
    findings = []
    score = scorer.score(findings)
    assert score.score == 100
    assert score.grade == "A"

    # Score 97 -> A (one LOW: 100-3)
    findings = [create_finding("LOW-001", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 97
    assert score.grade == "A"

    # Score 94 -> A (two LOW: 100-6)
    findings = [create_finding("LOW-001", FindingSeverity.LOW),
                create_finding("LOW-002", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 94
    assert score.grade == "A"

    # Score 91 -> A (three LOW: 100-9)
    findings = [create_finding("LOW-001", FindingSeverity.LOW),
                create_finding("LOW-002", FindingSeverity.LOW),
                create_finding("LOW-003", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 91
    assert score.grade == "A"

    # Score 88 -> B (four LOW: 100-12)
    findings = [create_finding("LOW-001", FindingSeverity.LOW),
                create_finding("LOW-002", FindingSeverity.LOW),
                create_finding("LOW-003", FindingSeverity.LOW),
                create_finding("LOW-004", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 88
    assert score.grade == "B"

    # Score 85 -> B (one HIGH: 100-15)
    findings = [create_finding("HIGH-001", FindingSeverity.HIGH)]
    score = scorer.score(findings)
    assert score.score == 85
    assert score.grade == "B"

    # Score 80 -> B (five MEDIUM: 100-40) - wait, 5*8=40, 100-40=60, that's D
    # Let me recalculate: to get 80 exactly, need -20 points
    # 2 MEDIUM + 2 LOW = 2*8 + 2*3 = 16+6=22 -> 78 (C)
    # 1 HIGH + 1 MEDIUM = 15+8=23 -> 77 (C)
    # 1 HIGH + 2 LOW = 15+6=21 -> 79 (C)
    # Actually, let's test what we can achieve and verify grades are correct

    # Score 79 -> C (one HIGH + two LOW: 100-15-6=79)
    findings = [create_finding("HIGH-001", FindingSeverity.HIGH),
                create_finding("LOW-001", FindingSeverity.LOW),
                create_finding("LOW-002", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 79
    assert score.grade == "C"

    # Score 70 -> C (ten MEDIUM: 100-80=20? No, 10*8=80, 100-80=20 -> F)
    # Let me do: 3 HIGH + 1 LOW = 3*15 + 3 = 45+3=48, 100-48=52 -> F
    # 2 HIGH + 2 MEDIUM = 2*15 + 2*8 = 30+16=46, 100-46=54 -> F
    # 1 HIGH + 3 MEDIUM = 15+24=39, 100-39=61 -> D
    # 1 HIGH + 4 MEDIUM = 15+32=47, 100-47=53 -> F
    # 5 MEDIUM = 5*8=40, 100-40=60 -> D

    findings = [create_finding(f"MED-{i}", FindingSeverity.MEDIUM) for i in range(5)]
    score = scorer.score(findings)
    assert score.score == 60  # 100 - 40
    assert score.grade == "D"

    # Score 69 -> D (need 31 points deduction)
    # 2 HIGH + 1 LOW = 2*15 + 3 = 30+3=33 -> 67 -> D
    findings = [create_finding("HIGH-001", FindingSeverity.HIGH),
                create_finding("HIGH-002", FindingSeverity.HIGH),
                create_finding("LOW-001", FindingSeverity.LOW)]
    score = scorer.score(findings)
    assert score.score == 67  # 100 - 33
    assert score.grade == "D"

    # Score 60 -> D (five MEDIUM as tested above)
    # Already tested with 5 MEDIUM = 60 -> D

    # Score 59 -> F (need 41 points deduction)
    # 1 CRITICAL + 1 HIGH + 1 MEDIUM = 25+15+8=48 -> 52 -> F
    # Actually that's 48, let me do: 1 CRITICAL + cool
    findings = [create_finding("CRIT-001", FindingSeverity.CRITICAL),
                create_finding("HIGH-001", FindingSeverity.HIGH),
                create_finding("MED-001", FindingSeverity.MEDIUM)]
    score = scorer.score(findings)
    assert score.score == 52  # 100 - 48
    assert score.grade == "F"

    # Score 0 -> F (deductions >= 100)
    findings = [create_finding(f"CRIT-{i}", FindingSeverity.CRITICAL) for i in range(4)]  # 4*25=100
    score = scorer.score(findings)
    assert score.score == 0  # Capped at 0
    assert score.grade == "F"


def test_multiple_findings_same_type():
    """Test multiple findings of the same severity."""
    scorer = QualityScorer()

    # Multiple LOW findings
    findings = [create_finding(f"LOW-{i}", FindingSeverity.LOW) for i in range(5)]
    score = scorer.score(findings)
    assert score.score == 85  # 100 - (5*3) = 85
    assert score.grade == "B"  # 85 is in B range (80-89)
    assert len(score.deductions) == 5
    assert score.finding_count == 5

    # Multiple MEDIUM findings
    findings = [create_finding(f"MED-{i}", FindingSeverity.MEDIUM) for i in range(3)]
    score = scorer.score(findings)
    assert score.score == 76  # 100 - (3*8) = 76
    assert score.grade == "C"  # 76 is in C range (70-79)
    assert len(score.deductions) == 3
    assert score.finding_count == 3

    # Multiple HIGH findings
    findings = [create_finding(f"HIGH-{i}", FindingSeverity.HIGH) for i in range(2)]
    score = scorer.score(findings)
    assert score.score == 70  # 100 - (2*15) = 70
    assert score.grade == "C"  # 70 is in C range (70-79)
    assert len(score.deductions) == 2
    assert score.finding_count == 2

    # Multiple CRITICAL findings
    findings = [create_finding(f"CRIT-{i}", FindingSeverity.CRITICAL) for i in range(3)]
    score = scorer.score(findings)
    assert score.score == 25  # 100 - (3*25) = 25
    assert score.grade == "F"  # 25 is in F range (0-59)
    assert len(score.deductions) == 3
    assert score.finding_count == 3


def test_mixed_severities():
    """Test score with mixed severity findings."""
    scorer = QualityScorer()

    # Mix: 1 CRITICAL, 2 HIGH, 3 MEDIUM, 4 LOW
    findings = [
        create_finding("CRIT-001", FindingSeverity.CRITICAL),
        create_finding("HIGH-001", FindingSeverity.HIGH),
        create_finding("HIGH-002", FindingSeverity.HIGH),
        create_finding("MED-001", FindingSeverity.MEDIUM),
        create_finding("MED-002", FindingSeverity.MEDIUM),
        create_finding("MED-003", FindingSeverity.MEDIUM),
        create_finding("LOW-001", FindingSeverity.LOW),
        create_finding("LOW-002", FindingSeverity.LOW),
        create_finding("LOW-003", FindingSeverity.LOW),
        create_finding("LOW-004", FindingSeverity.LOW),
    ]
    score = scorer.score(findings)

    # Deductions: 25 + (2*15) + (3*8) + (4*3) = 25 + 30 + 24 + 12 = 91
    assert score.score == 9  # 100 - 91
    assert score.grade == "F"
    assert len(score.deductions) == 10
    assert score.finding_count == 10


def test_deductions_capped_at_zero():
    """Test that score never goes below zero."""
    scorer = QualityScorer()

    # Create enough findings to exceed 100 points
    findings = [create_finding(f"CRIT-{i}", FindingSeverity.CRITICAL) for i in range(5)]  # 5*25=125
    score = scorer.score(findings)
    assert score.score == 0  # Should be capped at 0, not -25
    assert score.grade == "F"
    assert len(score.deductions) == 5
    assert score.finding_count == 5


def test_determinism():
    """Test that identical findings always produce identical scores."""
    scorer = QualityScorer()

    findings = [
        create_finding("TEST-001", FindingSeverity.HIGH),
        create_finding("TEST-002", FindingSeverity.MEDIUM),
        create_finding("TEST-003", FindingSeverity.LOW),
        create_finding("TEST-004", FindingSeverity.CRITICAL),
    ]

    # Run multiple times
    score1 = scorer.score(findings)
    score2 = scorer.score(findings)
    score3 = scorer.score(findings)

    # HIGH=15, MEDIUM=8, LOW=3, CRITICAL=25 -> 15+8+3+25=51 -> 100-51=49
    assert score1.score == score2.score == score3.score
    assert score1.grade == score2.grade == score3.grade
    assert score1.score == 49
    assert score1.grade == "F"
    assert len(score1.deductions) == len(score2.deductions) == len(score3.deductions)
    assert score1.deductions == score2.deductions == score3.deductions


def test_finding_order_independence():
    """Test that finding order doesn't affect final score or grade."""
    scorer = QualityScorer()

    # Same findings in different orders
    findings1 = [
        create_finding("A-RULE", FindingSeverity.LOW),
        create_finding("B-RULE", FindingSeverity.HIGH),
        create_finding("C-RULE", FindingSeverity.MEDIUM),
    ]

    findings2 = [
        create_finding("C-RULE", FindingSeverity.MEDIUM),
        create_finding("A-RULE", FindingSeverity.LOW),
        create_finding("B-RULE", FindingSeverity.HIGH),
    ]

    findings3 = [
        create_finding("B-RULE", FindingSeverity.HIGH),
        create_finding("C-RULE", FindingSeverity.MEDIUM),
        create_finding("A-RULE", FindingSeverity.LOW),
    ]

    score1 = scorer.score(findings1)
    score2 = scorer.score(findings2)
    score3 = scorer.score(findings3)

    # All should have same score and grade
    assert score1.score == score2.score == score3.score
    assert score1.grade == score2.grade == score3.grade
    assert score1.score == 74  # 100 - 3 - 15 - 8 = 74
    assert score1.grade == "C"

    # Deductions should be in same order due to deterministic sorting
    assert score1.deductions == score2.deductions == score3.deductions
    # Should be ordered by severity priority: HIGH, MEDIUM, LOW
    assert score1.deductions[0]["rule_id"] == "B-RULE"  # HIGH
    assert score1.deductions[1]["rule_id"] == "C-RULE"  # MEDIUM
    assert score1.deductions[2]["rule_id"] == "A-RULE"  # LOW


def test_evidence_rule_identity():
    """Test that deduction records correctly preserve rule_id, severity, and points."""
    scorer = QualityScorer()

    finding = create_finding("SPECIFIC-RULE-001", FindingSeverity.HIGH,
                           FindingCategory.DOCUMENTATION,
                           "Specific test finding",
                           "This is a test finding for validation")
    score = scorer.score([finding])

    assert len(score.deductions) == 1
    deduction = score.deductions[0]

    # Verify identity preservation
    assert deduction["rule_id"] == "SPECIFIC-RULE-001"
    assert deduction["severity"] == "high"
    assert deduction["points"] == 15

    # Verify no extra fields are accidentally added
    expected_keys = {"rule_id", "severity", "points"}
    assert set(deduction.keys()) == expected_keys


def test_scanresult_integration():
    """Test that ScanResult correctly includes and serializes quality_score."""
    from auditor.models.models import RepositoryProfile, Evidence
    from auditor.models.scan_result import ScanResult

    # Create minimal profile and evidence
    profile = RepositoryProfile(name="test-repo")
    evidence = [Evidence(
        id="test-evidence",
        type="metadata",
        source="test-source",
        content="test content"
    )]

    # Create a finding
    finding = create_finding("TEST-001", FindingSeverity.MEDIUM)
    findings = [finding]

    # Create quality score
    scorer = QualityScorer()
    quality_score = scorer.score(findings)

    # Create ScanResult
    scan_result = ScanResult(
        repository_profile=profile,
        evidence=evidence,
        findings=findings,
        quality_score=quality_score
    )

    # Verify quality_score is present
    assert scan_result.quality_score is not None
    assert scan_result.quality_score.score == 92  # 100 - 8
    assert scan_result.quality_score.grade == "A"
    assert len(scan_result.quality_score.deductions) == 1
    assert scan_result.quality_score.deductions[0]["rule_id"] == "TEST-001"
    assert scan_result.quality_score.finding_count == 1

    # Verify existing fields still work
    assert scan_result.total_evidence_count == 1
    assert scan_result.total_findings_count == 1
    assert scan_result.repository_profile.name == "test-repo"

    # Verify JSON serialization works
    json_data = scan_result.model_dump()
    assert "quality_score" in json_data
    assert json_data["quality_score"]["score"] == 92
    assert json_data["quality_score"]["grade"] == "A"
    assert len(json_data["quality_score"]["deductions"]) == 1
    assert json_data["quality_score"]["deductions"][0]["rule_id"] == "TEST-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


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