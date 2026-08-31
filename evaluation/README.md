# Evaluation Harness for Repository Quality Auditor

This directory contains the evaluation harness for the Repository Quality Auditor system. The harness is designed to rigorously evaluate the auditor's performance against an independent ground truth dataset.

## Why This Evaluation Exists

The evaluation harness serves several critical purposes:

1. **Objective Measurement**: Provides a measurable baseline against which future improvements can be compared
2. **Failure Detection**: Identifies specific failure patterns that guide targeted improvements
3. **Reproducibility**: Ensures evaluations can be consistently reproduced across different environments
4. **Independent Validation**: Uses ground truth labels that are independent of the auditor's own output

## Baseline Definition

The baseline evaluator uses a simple, deterministic rule:
- **Good**: Repository has a README file (common variants: README.md, README, README.txt, etc.) AND at least one test file
- **Not Good**: Otherwise

Test files are detected using common naming patterns (see the source code for details).

## Final Solution Definition

The final solution is the existing Repository Quality Auditor system, configured as follows:
- Runs the complete audit pipeline: Scanner → Analyzer → Scorer
- Output format: JSON
- LLM insights: Disabled (`--llm` flag not used)
- Binary prediction derived from quality score: Score ≥ 80 → "Good", Score < 80 → "Not Good"

## Ground Truth Philosophy

Ground truth labels are assigned by human experts based on an explicit quality rubric that evaluates observable repository characteristics. Crucially:

- Ground truth is **independent** of the auditor's output
- Labels are assigned before running the auditor to prevent bias
- The rubric focuses on tangible, observable qualities rather than the auditor's internal metrics

This independence ensures that the evaluation measures the auditor's actual performance rather than its conformity to its own metrics.

## Primary Metric = F1 Score

The F1 score is the primary metric because it provides a balanced measure of precision and recall:

- **Precision**: Of all repositories labeled "good" by the system, what fraction are actually good?
- **Recall**: Of all repositories that are actually good, what fraction did the system correctly identify?
- **F1**: Harmonic mean of precision and recall (2 × precision × recall / (precision + recall))

F1 is preferred over accuracy because it performs better on imbalanced datasets and provides insight into both false positives and false negatives.

## Secondary Metrics

The evaluation also reports:
- Precision and recall (individual components of F1)
- Accuracy (overall correctness)
- False Positive Rate (FPR): FP / (FP + TN)
- False Negative Rate (FNR): FN / (FN + TP)
- Raw confusion matrix values (TP, TN, FP, FN)

## Reproducibility

The evaluation harness ensures reproducibility through:

1. **Commit SHA Pinning**: Each repository is evaluated at a specific Git commit
2. **Deterministic Algorithms**: Both baseline and final systems are deterministic
3. **Caching**: Repositories are cached to ensure consistent evaluations
4. **Version Control**: The evaluation harness itself is version controlled
5. **Environment Isolation**: Uses explicit Python dependencies and avoids external state

## Dataset Structure

The evaluation dataset is designed to support comprehensive testing:

- **Multiple Languages**: At least 3 different programming languages
- **Size Variety**: Small, medium, and large repositories
- **Quality Spectrum**: High, medium, and low quality repositories
- **Edge Cases**: At least one deliberately challenging/superficially-good repository

## Why LLM is Excluded from Primary Benchmark

LLM insights are excluded from the primary benchmark because:

1. **Determinism**: LLM outputs can vary between runs due to temperature, model updates, etc.
2. **Isolation**: We want to evaluate the core auditing capabilities first
3. **Baseline Comparison**: The baseline is purely deterministic, so the final should be comparable
4. **Cost and Availability**: LLM usage requires API keys and incurs costs
5. **Focus**: Primary evaluation focuses on improving the deterministic core before adding LLM enhancements

LLM insights can be evaluated separately in experimental configurations.

## Why Repository Commit SHAs are Pinned

Pinning to specific commit SHAs ensures:

1. **Temporal Consistency**: The same repository state is evaluated every time
2. **External Change Immunity**: Protection against repository updates that could change the evaluation
3. **Debugging Capability**: Ability to go back and re-evaluate exactly the same state
4. **Scientific Rigor**: Essential for reproducible research
5. **Cache Effectiveness**: Enables effective caching of cloned repositories

Without commit pinning, evaluations would be unreliable and non-reproducible.

## Usage

See `REPRODUCTION.md` for detailed instructions on running the evaluation.