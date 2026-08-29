"""CLI entry point for repository quality auditor."""

import argparse
import sys
import json
from typing import List, NoReturn, Optional

from .analyzers.repository_scanner import RepositoryScanner
from .analyzers.repository_analyzer import RepositoryAnalyzer
from .scoring.quality_scorer import QualityScorer
from .models.models import RepositoryProfile, Evidence
from .models.scan_result import ScanResult
from .models.llm_insight import LLMInsight
from .llm.service import create_llm_service, LLMService


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Evidence-backed agentic system that evaluates an unfamiliar software repository"
    )
    parser.add_argument(
        "repository_path",
        help="Path to the repository to audit"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for audit report (default: stdout)",
        default=None
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM-assisted insights (requires OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.4.0"
    )

    args = parser.parse_args()

    try:
        # Scan the repository
        scanner = RepositoryScanner()
        profile, evidence = scanner.scan(args.repository_path)

        # Analyze the evidence to generate findings
        analyzer = RepositoryAnalyzer()
        findings = analyzer.analyze(profile, evidence)

        # Score the findings to generate quality score
        scorer = QualityScorer()
        quality_score = scorer.score(findings)

        # Generate LLM insights if requested
        llm_insights: Optional[LLMInsight] = None
        if args.llm:
            llm_service = create_llm_service()
            if llm_service is not None:
                llm_insights = llm_service.generate_insights(
                    profile, evidence, findings, quality_score
                )
                if llm_insights is None:
                    print("Warning: LLM insights generation returned no result.", file=sys.stderr)
            else:
                print("Info: LLM insights disabled (OPENAI_API_KEY not set).", file=sys.stderr)

        # Create scan result
        scan_result = ScanResult(
            repository_profile=profile,
            evidence=evidence,
            findings=findings,
            quality_score=quality_score,
            llm_insights=llm_insights,
        )

        if args.format == "json":
            output = json.dumps(scan_result.model_dump(), indent=2, default=str)
        else:  # text
            output = _format_text_output(scan_result)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Audit report written to {args.output}")
        else:
            print(output)

        sys.exit(0)

    except (ValueError, PermissionError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def _format_text_output(scan_result: ScanResult) -> str:
    """Format scan result as human-readable text."""
    profile = scan_result.repository_profile
    evidence = scan_result.evidence
    findings = scan_result.findings
    quality_score = scan_result.quality_score
    llm_insights = scan_result.llm_insights

    # Extract useful information from evidence for display
    detected_files = []
    detected_directories = []
    missing_items = []

    for ev in evidence:
        if ev.type == "file_content" and ev.metadata.get("detected"):
            detected_files.append(ev.source)
        elif ev.type == "structure" and ev.metadata.get("detected"):
            detected_directories.append(ev.source)
        elif ev.type == "metadata" and not ev.metadata.get("detected", True):
            missing_items.append(ev.source)

    # Get counts from profile metadata
    source_count = profile.metadata.get("source_file_count", 0)
    test_count = profile.metadata.get("test_file_count", 0)
    total_files = profile.file_count or 0
    total_dirs = profile.metadata.get("total_directories", 0)

    output = f"""Repository Quality Auditor Report
============================
Repository: {profile.name}
Path: {profile.metadata.get('resolved_path', 'unknown')}
Status: Scan completed
Scanner version: {scan_result.scanner_version}

File Statistics:
  Total files: {total_files}
  Source files: {source_count}
  Test files: {test_count}
  Total directories: {total_dirs}

Findings
{_format_findings(findings) if findings else "  None"}

Quality Score
  Score: {quality_score.score if quality_score else 0}/{quality_score.max_score if quality_score else 100}
  Grade: {quality_score.grade if quality_score else 'F'}

{"Deductions" if quality_score and quality_score.deductions else ""}
{_format_deductions(quality_score.deductions) if quality_score and quality_score.deductions else ""}

{"LLM Insights" if llm_insights else ""}
{_format_llm_insights(llm_insights) if llm_insights else ""}

Detected Project Files:
{_format_list(detected_files) if detected_files else "  None"}

Detected Directories:
{_format_list(detected_directories) if detected_directories else "  None"}

Missing Common Items:
{_format_list(missing_items) if missing_items else "  None"}

Evidence Collected: {scan_result.total_evidence_count}
Findings Generated: {scan_result.total_findings_count}
Quality Score: {quality_score.score if quality_score else 0}
"""
    return output


def _format_findings(findings: List) -> str:
    """Format findings for display."""
    if not findings:
        return "  None"

    lines = []
    for finding in findings:
        severity_label = finding.severity.value.upper()
        lines.append(f"  [{severity_label}] {finding.rule_id} {finding.title}")
    return "\n".join(lines)


def _format_deductions(deductions: List[dict]) -> str:
    """Format deductions for display."""
    if not deductions:
        return ""

    lines = []
    for deduction in deductions:
        severity_label = deduction["severity"].upper()
        lines.append(f"  {deduction['rule_id']} {severity_label}    -{deduction['points']}")
    return "\n".join(lines) + "\n"


def _format_llm_insights(insights: Optional[LLMInsight]) -> str:
    """Format LLM insights for display."""
    if insights is None:
        return ""

    lines = []
    lines.append(f"  Summary: {insights.summary}")
    if insights.explanations:
        lines.append("  Explanations:")
        for exp in insights.explanations:
            lines.append(f"    [{exp.rule_id}] {exp.explanation}")
    if insights.recommendations:
        lines.append("  Recommendations:")
        for rec in insights.recommendations:
            lines.append(f"    [{rec.rule_id}] {rec.recommendation}")
    if insights.risks:
        lines.append("  Risks:")
        for risk in insights.risks:
            lines.append(f"    [{risk.severity.upper()}] {risk.description}")
    return "\n".join(lines) + "\n"


def _format_list(items: List[str]) -> str:
    """Format a list of items for display."""
    # Sort and limit display for readability
    sorted_items = sorted(items)
    if len(sorted_items) <= 5:
        return "\n".join(f"  {item}" for item in sorted_items)
    else:
        displayed = sorted_items[:5]
        return "\n".join(f"  {item}" for item in displayed) + f"\n  ... and {len(sorted_items) - 5} more"


if __name__ == "__main__":
    main()