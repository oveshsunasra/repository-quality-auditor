#!/usr/bin/env python3
"""
Baseline evaluation: predict 'good' if repository has a README file and at least one test file.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

# Import the shared cache helper
from repository_cache import clone_or_update_repo, cache_path

# Common README file names
README_PATTERNS = [
    "README.md",
    "README",
    "README.txt",
    "README.rst",
    "README.markdown",
]

# Test file patterns by language (simplified)
TEST_PATTERNS = [
    "test_*.py",
    "*_test.py",
    "test_*.js",
    "*_test.js",
    "test_*.ts",
    "*_test.ts",
    "test_*.jsx",
    "*_test.jsx",
    "test_*.tsx",
    "*_test.tsx",
    "test_*.java",
    "*Test.java",
    "Tests.java",
    "test_*.cs",
    "*_test.cs",
    "test_*.rb",
    "*_test.rb",
    "test_*.go",
    "*_test.go",
    # Add more as needed
]


def has_readme(repo_path: Path) -> bool:
    """
    Check if the repository has a README file (common variants).
    """
    for name in README_PATTERNS:
        if (repo_path / name).is_file():
            return True
    return False


def has_test_file(repo_path: Path) -> bool:
    """
    Check if the repository has at least one test file matching common patterns.
    """
    # Exclude .git directory to avoid false positives
    for pattern in TEST_PATTERNS:
        # Use rglob to search recursively
        matches = list(repo_path.rglob(pattern))
        # Filter out any matches inside .git
        matches = [m for m in matches if ".git" not in str(m)]
        if matches:
            return True
    return False


def evaluate_repository(repo_path: Path) -> str:
    """
    Evaluate a single repository and return 'good' or 'not_good'.
    """
    if has_readme(repo_path) and has_test_file(repo_path):
        return "good"
    else:
        return "not_good"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run baseline evaluation (README + test file check)."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the dataset CSV file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write baseline prediction JSON files",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Use existing cached repositories (skip cloning step)",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache",
        help="Directory to store cloned repositories (default: .cache)",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_dir = Path(args.output_dir)
    cache_dir = Path(args.cache_dir)

    if not dataset_path.is_file():
        print(f"Error: Dataset not found: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    import csv

    with open(dataset_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Evaluating {len(rows)} repositories...", file=sys.stderr)

    for i, row in enumerate(row, start=1):
        case_id = row["case_id"]
        repo_url = row["repo_url"].strip()
        commit_sha = row["commit_sha"].strip()

        # Show progress
        if i % 5 == 0 or i == len(rows):
            print(f"  [{i}/{len(rows)}] Processing case {case_id}", file=sys.stderr)

        # Determine the local repository path
        if args.skip_clone:
            # Use existing cache; if it doesn't exist, skip this case
            repo_path = cache_path(repo_url, commit_sha, cache_dir)
            if not repo_path.is_dir():
                print(
                    f"  Warning: Cache not found for case {case_id} (skip-clone enabled). Skipping.",
                    file=sys.stderr,
                )
                continue
        else:
            # Clone or update the repository
            try:
                repo_path = clone_or_update_repo(repo_url, commit_sha, cache_dir)
            except Exception as e:
                print(
                    f"  Error processing case {case_id}: {e}",
                    file=sys.stderr,
                )
                continue

        # Evaluate
        try:
            prediction = evaluate_repository(repo_path)
        except Exception as e:
            print(
                f"  Error evaluating case {case_id}: {e}",
                file=sys.stderr,
            )
            continue

        # Write prediction JSON
        pred_file = output_dir / f"{case_id}.json"
        try:
            with open(pred_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "case_id": case_id,
                        "prediction": prediction,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            print(
                f"  Error writing prediction for case {case_id}: {e}",
                file=sys.stderr,
            )
            continue

    print("Baseline evaluation complete.", file=sys.stderr)


if __name__ == "__main__":
    main()