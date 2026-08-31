#!/usr/bin/env python3
"""
Final evaluation: run the auditor and predict 'good' if quality score >= 80.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Import the shared cache helper
from repository_cache import clone_or_update_repo, cache_path

def run_auditor(repo_path: Path) -> Optional[dict]:
    """
    Run the auditor on the given repository path and return the parsed JSON output.
    Returns None if the auditor fails.
    """
    # Ensure we are using the auditor from the current environment
    auditor_cmd = [sys.executable, "-m", "auditor.cli", str(repo_path), "--format", "json"]
    # Disable LLM insights by emptying the API key
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = ""
    try:
        result = subprocess.run(
            auditor_cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,  # We'll handle non-zero exit codes ourselves
        )
        if result.returncode != 0:
            print(
                f"  Auditor failed with exit code {result.returncode}: {result.stderr[:200]}",
                file=sys.stderr,
            )
            return None
        # Parse JSON output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"  Failed to parse auditor JSON output: {e}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  Error running auditor: {e}", file=sys.stderr)
        return None

def evaluate_repository(repo_path: Path) -> str:
    """
    Evaluate a single repository and return 'good' or 'not_good'.
    """
    auditor_output = run_auditor(repo_path)
    if auditor_output is None:
        # If the auditor fails, we cannot make a prediction; treat as not_good? Or skip?
        # We'll skip by returning None, but the caller will handle skipping.
        return None
    score = auditor_output.get("quality_score", {}).get("score")
    if score is None:
        print("  Auditor output missing quality_score", file=sys.stderr)
        return None
    try:
        score_val = float(score)
    except (ValueError, TypeError):
        print(f"  Invalid score value: {score}", file=sys.stderr)
        return None
    return "good" if score_val >= 80.0 else "not_good"

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run final evaluation (auditor with score >= 80 -> good)."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the dataset CSV file",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write final prediction JSON files",
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

    for i, row in enumerate(rows, start=1):
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
            if prediction is None:
                print(
                    f"  Skipping case {case_id} due to auditor error.",
                    file=sys.stderr,
                )
                continue
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

    print("Final evaluation complete.", file=sys.stderr)


if __name__ == "__main__":
    main()