# Reproducibility Guide for Repository Quality Auditor Evaluation

This document describes how to reproduce the evaluation of the Repository Quality Auditor system.

## 1. Python Version

- Python 3.12 or higher is required
- The evaluation harness has been tested with Python 3.12

## 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd repository-quality-auditor

# Install in development mode
pip install -e .
```

## 3. Dataset Format

The evaluation dataset is a CSV file with the following columns:

- `case_id`: Unique identifier for each repository
- `repo_url`: URL of the Git repository
- `commit_sha`: Specific Git commit SHA to evaluate
- `primary_language`: Primary programming language of the repository
- `file_count`: Number of files in the repository (informational)
- `ground_truth_label`: Human-assigned label (`good` or `not_good`)
- `evidence_for_label`: Explanation of why the label was assigned
- `notes`: Additional notes about the repository
- `case_type`: Category (`standard` or `challenging`)

See `dataset.example.csv` for the expected format.

## 4. Repository Pinning

Each evaluation repository is pinned to a specific Git commit SHA to ensure reproducibility. The evaluation harness:

1. Clones the repository at the specified URL
2. Checks out the exact commit SHA specified in the dataset
3. Verifies the checkout before evaluation
4. Uses a local cache to avoid re-cloning the same repository/commit combination

## 5. Baseline Command

To run the baseline evaluation (README + test file check):

```bash
python evaluation/run_baseline.py \
    --dataset evaluation/dataset.csv \
    --cache-dir evaluation/.cache \
    --output-dir evaluation/results/baseline
```

Options:
- `--skip-clone`: Use existing cached repositories (skip cloning step)
- `--cache-dir`: Directory to store cloned repositories (default: `.cache`)
- `--output-dir`: Directory to write baseline results

## 6. Final Command

To run the final evaluation (using the Repository Quality Auditor):

```bash
python evaluation/run_final.py \
    --dataset evaluation/dataset.csv \
    --cache-dir evaluation/.cache \
    --output-dir evaluation/results/final
```

Options:
- `--skip-clone`: Use existing cached repositories (skip cloning step)
- `--cache-dir`: Directory to store cloned repositories (default: `.cache`)
- `--output-dir`: Directory to write final results

**Important**: The auditor is run with `--format json` and without the `--llm` flag to ensure deterministic results.

## 7. Metrics Command

To compute evaluation metrics comparing baseline and final results:

```bash
python evaluation/compute_metrics.py \
    --dataset evaluation/dataset.csv \
    --baseline-dir evaluation/results/baseline \
    --final-dir evaluation/results/final \
    --output evaluation/results/summary.json
```

This will:
1. Load ground truth labels from the dataset
2. Load baseline and final predictions
3. Compute confusion matrices (TP, TN, FP, FN)
4. Calculate precision, recall, F1, accuracy, FPR, and FNR
5. Write a summary JSON file and print a human-readable report

## 8. Expected Output Locations

- Baseline results: `evaluation/results/baseline/` (one JSON file per case)
- Final results: `evaluation/results/final/` (one JSON file per case)
- Summary metrics: `evaluation/results/summary.json`
- Cached repositories: `evaluation/.cache/` (one directory per repo/commit)

## 9. Fixed Score Threshold

For the final evaluation, the Repository Quality Auditor's quality score is converted to a binary prediction using a fixed threshold:

- Score ≥ 80 → `good`
- Score < 80 → `not_good`

This threshold is based on the grading system defined in the documentation (80-89 = B grade) and is not optimized against the evaluation dataset.

## 10. LLM Disabled for Primary Benchmark

The primary benchmark runs the Auditor with LLM insights disabled (`--llm` flag not used) to ensure:

1. Deterministic, reproducible results
2. Evaluation of the core auditing capabilities without external variability
3. Fair comparison with the baseline (which is also deterministic)
4. Compliance with the requirement that LLM insights do not affect authoritative findings

LLM insights can be enabled separately for experimental evaluation.

## 11. Ground Truth Independence

Ground truth labels are assigned independently of the Auditor's output based on an explicit repository-quality rubric considering:

- Documentation adequacy
- Meaningful tests
- Dependency/build reproducibility
- Source-code substance
- Basic repository hygiene

The Auditor's own finding IDs, quality score, or analyzer output are NOT used to define ground truth.

## 12. Troubleshooting

### Common Issues

1. **Git clone failures**: Check network connectivity and repository accessibility
2. **Missing dependencies**: Ensure Python 3.12+ is installed and `pip install -e .` was run
3. **Permission errors**: On Windows, some permission-related tests may be skipped
4. **Cache issues**: Use `--skip-clone` to avoid re-cloning, or delete the cache directory to start fresh

### Getting Help

If you encounter issues, check:
1. The error messages printed during execution
2. The existence of required files and directories
3. Python version and installed packages