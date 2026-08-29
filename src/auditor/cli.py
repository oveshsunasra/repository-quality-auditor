"""CLI entry point for repository quality auditor."""

import argparse
import sys
import json
from typing import NoReturn

from .models.models import RepositoryProfile, Evidence, Finding, AuditReport


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

    # For now, just create a basic report structure
    # This will be expanded in future iterations
    profile = RepositoryProfile(
        name=args.repository_path.split("/")[-1] if "/" in args.repository_path else args.repository_path,
        description="Repository audit in progress"
    )

    report = AuditReport(
        repository_profile=profile,
        evidence=[],
        findings=[],
        summary={
            "status": "baseline",
            "message": "Repository Quality Auditor - Baseline implementation",
            "next_steps": [
                "Implement analyzers",
                "Implement agents",
                "Add scoring mechanism",
                "Implement multi-agent workflow"
            ]
        }
    )

    if args.format == "json":
        output = json.dumps(report.model_dump(), indent=2, default=str)
    else:  # text
        output = f"""Repository Quality Auditor Report
============================
Repository: {profile.name}
Description: {profile.description}
Status: Baseline implementation
Evidence collected: {len(report.evidence)}
Findings: {len(report.findings)}

This is a baseline implementation. Future versions will include:
- Actual repository analysis
- Evidence collection
- Finding generation
- Scoring and recommendations
"""

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Audit report written to {args.output}")
    else:
        print(output)

    sys.exit(0)


if __name__ == "__main__":
    main()