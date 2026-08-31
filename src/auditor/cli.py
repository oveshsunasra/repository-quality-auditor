"""CLI entry point for repository quality auditor."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, NoReturn, Optional
from urllib.parse import urlsplit

from .analyzers.repository_scanner import RepositoryScanner
from .analyzers.repository_analyzer import RepositoryAnalyzer
from .scoring.quality_scorer import QualityScorer
from .models.models import RepositoryProfile, Evidence
from .models.scan_result import ScanResult
from .models.llm_insight import LLMInsight
from .llm.service import create_llm_service, LLMService


GIT_CLONE_TIMEOUT_SECONDS = 300


def _is_http_url(value: str) -> bool:
    """Return whether a value is an HTTP(S) URL candidate."""
    return value.startswith(("http://", "https://"))


def _parse_github_repository_url(value: str) -> str:
    """Validate a supported public GitHub HTTPS repository URL.

    Returns a canonical URL without a trailing ``.git``. This deliberately
    supports only the public GitHub URL forms documented by the CLI.
    """
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Unsupported repository URL. Use https://github.com/OWNER/REPOSITORY"
        )

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) != 2:
        raise ValueError(
            "Unsupported repository URL. Use https://github.com/OWNER/REPOSITORY"
        )

    owner, repository = path_parts
    if repository.endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository or any(
        character.isspace() for character in f"{owner}{repository}"
    ):
        raise ValueError(
            "Unsupported repository URL. Use https://github.com/OWNER/REPOSITORY"
        )

    return f"https://github.com/{owner}/{repository}"


def _remove_directory(path: Path) -> None:
    """Best-effort removal of a temporary clone, including read-only files."""

    def make_writable_and_retry(function, target, _exc_info):
        try:
            os.chmod(target, 0o700)
            function(target)
        except OSError:
            pass

    shutil.rmtree(path, onerror=make_writable_and_retry)


def _clone_github_repository(url: str) -> Path:
    """Clone a validated public GitHub URL into a newly-created temp directory."""
    if shutil.which("git") is None:
        raise RuntimeError("git is required to audit a repository URL but was not found in PATH")

    clone_dir = Path(tempfile.mkdtemp(prefix="repository-quality-auditor-"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(clone_dir)],
            check=True,
            capture_output=True,
            timeout=GIT_CLONE_TIMEOUT_SECONDS,
        )
        return clone_dir
    except subprocess.TimeoutExpired as error:
        _remove_directory(clone_dir)
        raise RuntimeError(
            "Timed out while cloning the GitHub repository "
            f"after {error.timeout} seconds"
        ) from error
    except subprocess.CalledProcessError as error:
        _remove_directory(clone_dir)
        raise RuntimeError(
            "Unable to clone the GitHub repository "
            f"(git exited with status {error.returncode}). "
            "Verify that the repository is public and accessible."
        ) from error
    except OSError as error:
        _remove_directory(clone_dir)
        raise RuntimeError(f"Unable to start git: {error}") from error


def main() -> NoReturn:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Evidence-backed agentic system that evaluates an unfamiliar software repository"
    )
    parser.add_argument(
        "repository_path",
        help="Local repository path or public GitHub HTTPS URL"
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
        "--keep-clone",
        action="store_true",
        help="Keep a temporary clone made for a GitHub URL after the audit"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.4.0"
    )

    args = parser.parse_args()
    temporary_clone: Optional[Path] = None
    scan_path = args.repository_path

    try:
        if _is_http_url(args.repository_path):
            github_url = _parse_github_repository_url(args.repository_path)
            temporary_clone = _clone_github_repository(github_url)
            scan_path = str(temporary_clone)

        # Scan the repository.
        scanner = RepositoryScanner()
        profile, evidence = scanner.scan(scan_path)

        # Analyze the evidence to generate findings.
        analyzer = RepositoryAnalyzer()
        findings = analyzer.analyze(profile, evidence)

        # Score the findings to generate quality score.
        scorer = QualityScorer()
        quality_score = scorer.score(findings)

        # Generate LLM insights if requested.
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

        # Create scan result.
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

    except (ValueError, PermissionError, OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Unexpected error: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        if temporary_clone is not None:
            if args.keep_clone:
                print(f"Temporary clone preserved at: {temporary_clone}", file=sys.stderr)
            elif temporary_clone.exists():
                _remove_directory(temporary_clone)


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
