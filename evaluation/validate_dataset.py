#!/usr/bin/env python3
"""
Validate the evaluation dataset.

Checks:
- SHA format (40 hex characters)
- No duplicate URLs
- No duplicate SHAs
- Allowed ground_truth_label values (good/not_good)
- Allowed case_type values (standard/challenging)
- Non-empty evidence and notes fields
"""

import csv
import re
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python validate_dataset.py <dataset.csv>")
        sys.exit(1)

    dataset_path = Path(sys.argv[1])
    if not dataset_path.is_file():
        print(f"Error: Dataset not found: {dataset_path}")
        sys.exit(1)

    errors = []
    seen_urls = set()
    seen_shas = set()

    with open(dataset_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Expect columns: case_id, repo_url, commit_sha, primary_language, file_count,
        # ground_truth_label, evidence_for_label, notes, case_type
        required_columns = {
            "case_id",
            "repo_url",
            "commit_sha",
            "primary_language",
            "file_count",
            "ground_truth_label",
            "evidence_for_label",
            "notes",
            "case_type",
        }
        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            print(f"Error: Missing columns: {missing}")
            sys.exit(1)

        for i, row in enumerate(reader, start=2):  # line numbers start at 2 (header is line 1)
            case_id = row["case_id"]
            repo_url = row["repo_url"].strip()
            commit_sha = row["commit_sha"].strip()
            ground_truth_label = row["ground_truth_label"].strip()
            case_type = row["case_type"].strip()
            evidence = row["evidence_for_label"].strip()
            notes = row["notes"].strip()

            # SHA format: 40 hex characters
            if not re.fullmatch(r"[0-9a-f]{40}", commit_sha, re.IGNORECASE):
                errors.append(f"Line {i}: Invalid SHA format for case {case_id}: {commit_sha}")

            # No duplicate URLs
            if repo_url in seen_urls:
                errors.append(f"Line {i}: Duplicate URL: {repo_url}")
            seen_urls.add(repo_url)

            # No duplicate SHAs
            if commit_sha in seen_shas:
                errors.append(f"Line {i}: Duplicate SHA: {commit_sha}")
            seen_shas.add(commit_sha)

            # Allowed ground_truth_label values
            if ground_truth_label not in {"good", "not_good"}:
                errors.append(f"Line {i}: Invalid ground_truth_label: {ground_truth_label}")

            # Allowed case_type values
            if case_type not in {"standard", "challenging"}:
                errors.append(f"Line {i}: Invalid case_type: {case_type}")

            # Non-empty evidence and notes
            if not evidence:
                errors.append(f"Line {i}: Empty evidence_for_label")
            if not notes:
                errors.append(f"Line {i}: Empty notes")

    if errors:
        print("Validation failed:")
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("VALIDATION PASSED: All checks passed.")


if __name__ == "__main__":
    main()