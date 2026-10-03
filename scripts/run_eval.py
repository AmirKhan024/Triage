"""Benchmark evaluation script for Experiment 1 (E1) and test dataset auditing.

Strictly follows:
- Rule D3: Only script authorized to read official test split.
- Rule V-4: All reported numbers stored in results/ JSON.
- Rule V-5: 95% bootstrap confidence intervals with fixed seed.
- Prompt requirement: Write test set per-repo/per-class counts and
  train-test (repo, title, body) duplicate overlap count into results/data_report.json.
"""

import json
import sys
from pathlib import Path

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.config import BOOTSTRAP_SAMPLES
from triage.data.loaders import load_dataset
from triage.eval.metrics import compute_bootstrap_cis
from triage.ml.classifier import M1Classifier
from triage.ml.preprocess import preprocess_text


def update_data_report_with_test_counts(
    test_df,
    train_df,
    data_report_path: Path,
) -> None:
    """Audit official test set and update results/data_report.json before scoring."""
    with open(data_report_path, encoding="utf-8") as f:
        data_report = json.load(f)

    # Per-repository and per-class counts of official test set
    test_repos = sorted(test_df["repo"].unique().tolist())
    test_labels = sorted(test_df["label"].unique().tolist())
    repo_counts = test_df["repo"].value_counts().to_dict()
    label_counts = test_df["label"].value_counts().to_dict()

    repo_label_breakdown = {}
    for repo in test_repos:
        r_df = test_df[test_df["repo"] == repo]
        repo_label_breakdown[repo] = r_df["label"].value_counts().to_dict()

    # Number of rows whose (repo, title, body) appears in both official train and test
    def make_row_key(df):
        return [
            (str(r).strip(), str(t).strip(), str(b).strip())
            for r, t, b in zip(df["repo"], df["title"], df["body"].fillna(""), strict=False)
        ]

    train_keys = set(make_row_key(train_df))
    test_keys = make_row_key(test_df)
    overlap_count = sum(1 for key in test_keys if key in train_keys)

    # Update data_report (counts only)
    data_report["official_test_set"] = {
        "total_count": len(test_df),
        "repositories": test_repos,
        "labels": test_labels,
        "counts_per_repo": repo_counts,
        "counts_per_label": label_counts,
        "counts_per_repo_and_label": repo_label_breakdown,
    }
    data_report["train_test_overlap_count"] = overlap_count

    with open(data_report_path, "w", encoding="utf-8") as f:
        json.dump(data_report, f, indent=2)

    print(f"Updated {data_report_path} with official test set counts:")
    print(f"  Test rows: {len(test_df)}")
    print(f"  Rows with (repo, title, body) in both official train & test: {overlap_count}")


def run_e1_eval(
    test_path: Path | str | None = None,
    train_path: Path | str | None = None,
    model_path: Path | str | None = None,
    results_dir: Path | str | None = None,
    n_bootstraps: int = BOOTSTRAP_SAMPLES,
    seed: int = 42,
) -> dict:
    root = Path(__file__).resolve().parent.parent
    if test_path is None:
        test_path = root / "data" / "issues_test.csv"
    if train_path is None:
        train_path = root / "data" / "issues_train.csv"
    if model_path is None:
        model_path = root / "models" / "classifier.joblib"
    if results_dir is None:
        results_dir = root / "results"

    test_path = Path(test_path)
    train_path = Path(train_path)
    model_path = Path(model_path)
    results_dir = Path(results_dir)
    data_report_path = results_dir / "data_report.json"

    # Step 1: Load official test and train sets
    print(f"Loading official test set from {test_path}...")
    test_df = load_dataset(test_path)
    print(f"Loading official train set for overlap checking from {train_path}...")
    train_df = load_dataset(train_path)

    # Step 2: Before scoring, write counts to results/data_report.json
    update_data_report_with_test_counts(test_df, train_df, data_report_path)

    # Step 3: Load trained M1 classifier
    print(f"Loading trained classifier from {model_path}...")
    model = M1Classifier.load(model_path)

    # Step 4: Preprocess test issues
    print(f"Preprocessing {len(test_df)} test samples...")
    test_texts = [
        preprocess_text(str(t), str(b))
        for t, b in zip(test_df["title"], test_df["body"].fillna(""), strict=False)
    ]
    test_labels = test_df["label"].tolist()
    test_repos = test_df["repo"].tolist()

    # Step 5: Predict
    print("Running predictions...")
    preds = model.predict(test_texts)

    # Step 6: Compute metrics with 95% bootstrap confidence intervals
    print(
        f"Computing 95% bootstrap confidence intervals ({n_bootstraps} resamples, seed={seed})..."
    )
    bootstrap_results = compute_bootstrap_cis(
        y_true=test_labels,
        y_pred=preds,
        repos=test_repos,
        n_bootstraps=n_bootstraps,
        seed=seed,
    )

    # Published comparisons from Section 4.1
    published_comparisons = {
        "baseline_overall_f1": 0.8270,
        "strongest_published_f1": 0.8934,
        "baseline_per_repo_f1": {
            "facebook/react": 0.8718,
            "tensorflow/tensorflow": 0.8644,
            "microsoft/vscode": 0.8262,
            "opencv/opencv": 0.8173,
            "bitcoin/bitcoin": 0.7555,
        },
        "baseline_per_class_f1": {
            "bug": 0.8426,
            "feature": 0.8558,
            "question": 0.7827,
        },
    }

    e1_output = {
        "experiment": "E1",
        "model": "M1_TFIDF_LogisticRegression",
        "description": "M1 evaluated on official benchmark test set with 95% bootstrap confidence intervals",
        "test_sample_count": len(test_df),
        "bootstrap_samples": n_bootstraps,
        "seed": seed,
        "macro_metrics": {
            "f1": bootstrap_results["macro_f1"],
            "precision": bootstrap_results["macro_precision"],
            "recall": bootstrap_results["macro_recall"],
        },
        "per_class": bootstrap_results["per_class"],
        "per_repo": bootstrap_results["per_repo"],
        "published_comparisons": published_comparisons,
    }

    # Save to results/e1_results.json
    e1_path = results_dir / "e1_results.json"
    with open(e1_path, "w", encoding="utf-8") as f:
        json.dump(e1_output, f, indent=2)

    print(f"\nE1 results saved to {e1_path}")
    print(
        f"M1 Average Macro F1: {bootstrap_results['macro_f1']['score']:.4f} "
        f"[95% CI: {bootstrap_results['macro_f1']['ci_95'][0]:.4f}, "
        f"{bootstrap_results['macro_f1']['ci_95'][1]:.4f}]"
    )
    print("Per-repository Macro F1 vs Published Baseline:")
    for repo, data in bootstrap_results["per_repo"].items():
        base_f1 = published_comparisons["baseline_per_repo_f1"].get(repo, "N/A")
        print(
            f"  {repo}: M1={data['macro_f1']['score']:.4f} "
            f"[95% CI: {data['macro_f1']['ci_95'][0]:.4f}, {data['macro_f1']['ci_95'][1]:.4f}] "
            f"(Baseline: {base_f1})"
        )

    return e1_output


if __name__ == "__main__":
    run_e1_eval()
