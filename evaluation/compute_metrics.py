#!/usr/bin/env python3
"""
Compute evaluation metrics comparing baseline and final results.
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_dataset(dataset_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load the dataset and return a dict mapping case_id to a dict with
    ground_truth_label and case_type.
    """
    data = {}
    with open(dataset_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            case_id = row["case_id"]
            data[case_id] = {
                "ground_truth_label": row["ground_truth_label"].strip(),
                "case_type": row["case_type"].strip(),
            }
    return data


def load_predictions(
    pred_dir: Path, case_ids: List[str]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Load predictions from JSON files in pred_dir.
    Returns a dict mapping case_id to prediction (good/not_good) and a list of errors.
    """
    predictions: Dict[str, str] = {}
    errors: List[str] = []
    for case_id in case_ids:
        pred_file = pred_dir / f"{case_id}.json"
        if not pred_file.is_file():
            errors.append(f"Missing prediction file for case {case_id}: {pred_file}")
            continue
        try:
            with open(pred_file, encoding="utf-8") as f:
                pred_data = json.load(f)
            prediction = pred_data.get("prediction")
            if prediction not in {"good", "not_good"}:
                errors.append(
                    f"Invalid prediction in {pred_file}: {prediction} (expected 'good' or 'not_good')"
                )
                continue
            predictions[case_id] = prediction
        except (json.JSONDecodeError, KeyError) as e:
            errors.append(f"Error reading {pred_file}: {e}")
    return predictions, errors


def compute_metrics(
    ground_truth: Dict[str, str],
    predictions: Dict[str, str],
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """
    Compute confusion matrix and derived metrics.
    Returns (confusion_dict, metrics_dict) where:
        confusion_dict: TP, TN, FP, FN
        metrics_dict: precision, recall, f1, accuracy, fpr, fnr
    """
    tp = tn = fp = fn = 0
    for case_id, gt_label in ground_truth.items():
        if case_id not in predictions:
            continue
        pred_label = predictions[case_id]
        if gt_label == "good" and pred_label == "good":
            tp += 1
        elif gt_label == "not_good" and pred_label == "not_good":
            tn += 1
        elif gt_label == "not_good" and pred_label == "good":
            fp += 1
        elif gt_label == "good" and pred_label == "not_good":
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    confusion = {"tp": tp, "tn": tn, "fp": fp, "fn": fn}
    metrics = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
    }
    return confusion, metrics


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute evaluation metrics comparing baseline and final results."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the dataset CSV file",
    )
    parser.add_argument(
        "--baseline-dir",
        required=True,
        help="Directory containing baseline prediction JSON files",
    )
    parser.add_argument(
        "--final-dir",
        required=True,
        help="Directory containing final prediction JSON files",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write summary JSON file",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    baseline_dir = Path(args.baseline_dir)
    final_dir = Path(args.final_dir)
    output_path = Path(args.output)

    if not dataset_path.is_file():
        print(f"Error: Dataset not found: {dataset_path}")
        sys.exit(1)
    if not baseline_dir.is_dir():
        print(f"Error: Baseline directory not found: {baseline_dir}")
        sys.exit(1)
    if not final_dir.is_dir():
        print(f"Error: Final directory not found: {final_dir}")
        sys.exit(1)

    # Load dataset
    dataset = load_dataset(dataset_path)
    case_ids = sorted(dataset.keys())

    # Load predictions
    baseline_pred, baseline_errors = load_predictions(baseline_dir, case_ids)
    final_pred, final_errors = load_predictions(final_dir, case_ids)

    # Report errors
    all_errors = baseline_errors + final_errors
    if all_errors:
        print("Errors encountered while loading predictions:")
        for err in all_errors:
            print(err)
        # We continue anyway, but note that missing cases will be skipped in metrics

    # Compute metrics for baseline and final over the intersection of cases
    # that have predictions in both (or at least one? We'll compute for cases that have predictions)
    # We'll compute for cases that have predictions in the respective set.
    baseline_truth = {
        cid: dataset[cid]["ground_truth_label"]
        for cid in baseline_pred.keys()
        if cid in dataset
    }
    final_truth = {
        cid: dataset[cid]["ground_truth_label"]
        for cid in final_pred.keys()
        if cid in dataset
    }

    baseline_confusion, baseline_metrics = compute_metrics(baseline_truth, baseline_pred)
    final_confusion, final_metrics = compute_metrics(final_truth, final_pred)

    # Compute improvements
    improvement = {
        "f1_improvement": final_metrics["f1"] - baseline_metrics["f1"],
        "accuracy_improvement": final_metrics["accuracy"] - baseline_metrics["accuracy"],
        "precision_improvement": final_metrics["precision"] - baseline_metrics["precision"],
        "recall_improvement": final_metrics["recall"] - baseline_metrics["recall"],
    }

    # Prepare summary
    summary = {
        "dataset": str(dataset_path),
        "baseline": {
            "confusion_matrix": baseline_confusion,
            "metrics": baseline_metrics,
        },
        "final": {
            "confusion_matrix": final_confusion,
            "metrics": final_metrics,
        },
        "improvement": improvement,
    }

    # Write summary JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print human-readable report
    print("\n=== Baseline ===")
    print(
        f"TP={baseline_confusion['tp']}, TN={baseline_confusion['tn']}, "
        f"FP={baseline_confusion['fp']}, FN={baseline_confusion['fn']}"
    )
    print(
        f"Precision: {baseline_metrics['precision']:.3f}, "
        f"Recall: {baseline_metrics['recall']:.3f}, "
        f"F1: {baseline_metrics['f1']:.3f}, "
        f"Accuracy: {baseline_metrics['accuracy']:.3f}"
    )
    print(
        f"FPR: {baseline_metrics['false_positive_rate']:.3f}, "
        f"FNR: {baseline_metrics['false_negative_rate']:.3f}"
    )

    print("\n=== Final ===")
    print(
        f"TP={final_confusion['tp']}, TN={final_confusion['tn']}, "
        f"FP={final_confusion['fp']}, FN={final_confusion['fn']}"
    )
    print(
        f"Precision: {final_metrics['precision']:.3f}, "
        f"Recall: {final_metrics['recall']:.3f}, "
        f"F1: {final_metrics['f1']:.3f}, "
        f"Accuracy: {final_metrics['accuracy']:.3f}"
    )
    print(
        f"FPR: {final_metrics['false_positive_rate']:.3f}, "
        f"FNR: {final_metrics['false_negative_rate']:.3f}"
    )

    print("\n=== Improvement (Final - Baseline) ===")
    print(f"F1: {improvement['f1_improvement']:+.3f}")
    print(f"Accuracy: {improvement['accuracy_improvement']:+.3f}")
    print(f"Precision: {improvement['precision_improvement']:+.3f}")
    print(f"Recall: {improvement['recall_improvement']:+.3f}")


if __name__ == "__main__":
    main()