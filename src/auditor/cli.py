"""CLI entry point for repository quality auditor."""

import argparse
import sys
import json
from typing import List, NoReturn

from .analyzers.repository_scanner import RepositoryScanner
from .models.models import RepositoryProfile, Evidence
from .models.scan_result import ScanResult


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
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    args = parser.parse_args()

    try:
        # Scan the repository
        scanner = RepositoryScanner()
        profile, evidence = scanner.scan(args.repository_path)

        # Create scan result
        scan_result = ScanResult(
            repository_profile=profile,
            evidence=evidence,
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

Detected Project Files:
{_format_list(detected_files) if detected_files else "  None"}

Detected Directories:
{_format_list(detected_directories) if detected_directories else "  None"}

Missing Common Items:
{_format_list(missing_items) if missing_items else "  None"}

Evidence Collected: {scan_result.total_evidence_count}

This is a deterministic repository scan. Future versions will include:
- Specialized analyzers (security, performance, etc.)
- Agent coordination
- Scoring and recommendations
"""
    return output


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