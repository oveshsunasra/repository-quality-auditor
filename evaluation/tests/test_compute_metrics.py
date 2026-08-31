"""
Tests for the evaluation harness metrics computation.
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from compute_metrics import load_dataset, load_predictions, compute_metrics


def test_load_dataset():
    """Test loading a dataset CSV."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("""case_id,repo_url,commit_sha,primary_language,file_count,ground_truth_label,evidence_for_label,notes,case_type
001,https://github.com/example/repo1,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,Python,10,good,Has README and tests,Some notes,standard
002,https://github.com/example/repo2,bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,JavaScript,5,not_good,Missing tests,Some notes,challenging
""")
        dataset_path = Path(f.name)

    try:
        data = load_dataset(dataset_path)
        assert len(data) == 2
        assert data["001"]["ground_truth_label"] == "good"
        assert data["001"]["case_type"] == "standard"
        assert data["002"]["ground_truth_label"] == "not_good"
        assert data["002"]["case_type"] == "challenging"
    finally:
        dataset_path.unlink()


def test_load_predictions():
    """Test loading prediction JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pred_dir = Path(tmpdir)
        # Create prediction files
        (pred_dir / "001.json").write_text('{"case_id": "001", "prediction": "good"}')
        (pred_dir / "002.json").write_text('{"case_id": "002", "prediction": "not_good"}')
        # Missing file for 003
        case_ids = ["001", "002", "003"]
        predictions, errors = load_predictions(pred_dir, case_ids)
        assert len(predictions) == 2
        assert predictions["001"] == "good"
        assert predictions["002"] == "not_good"
        assert len(errors) == 1
        assert "Missing prediction file" in errors[0]


def test_compute_metrics():
    """Test metric computation."""
    ground_truth = {
        "001": "good",
        "002": "not_good",
        "003": "good",
        "004": "not_good",
    }
    predictions = {
        "001": "good",   # TP
        "002": "good",   # FP
        "003": "not_good", # FN
        "004": "not_good", # TN
    }
    confusion, metrics = compute_metrics(ground_truth, predictions)
    assert confusion["tp"] == 1
    assert confusion["tn"] == 1
    assert confusion["fp"] == 1
    assert confusion["fn"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["accuracy"] == 0.5
    assert metrics["false_positive_rate"] == 0.5
    assert metrics["false_negative_rate"] == 0.5


def test_edge_cases():
    """Test edge cases like empty predictions."""
    ground_truth = {"001": "good"}
    predictions = {}  # No predictions
    confusion, metrics = compute_metrics(ground_truth, predictions)
    assert confusion["tp"] == 0
    assert confusion["tn"] == 0
    assert confusion["fp"] == 0
    assert confusion["fn"] == 0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0
    assert metrics["accuracy"] == 0.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["false_negative_rate"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])