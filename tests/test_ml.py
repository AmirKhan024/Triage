"""Tests for ML classifier and evaluation metrics."""

import json
from pathlib import Path

import pytest

from triage.eval.metrics import compute_bootstrap_cis
from triage.ml.classifier import M1Classifier, build_m1_pipeline


def test_build_m1_pipeline():
    pipeline = build_m1_pipeline()
    assert "features" in pipeline.named_steps
    assert "clf" in pipeline.named_steps


def test_m1_classifier_fit_and_predict():
    texts = [
        "crash on startup with traceback",
        "add support for dark mode feature",
        "how do I install this package on windows?",
        "fatal error memory leak in c++",
        "request to add new api endpoint",
        "where is the configuration file located?",
    ]
    labels = ["bug", "feature", "question", "bug", "feature", "question"]

    model = M1Classifier()
    model.fit(texts, labels)

    preds = model.predict(texts)
    assert len(preds) == len(texts)

    pred_label, conf, probas = model.predict_issue("runtime exception in module", "details here")
    assert pred_label in ["bug", "feature", "question"]
    assert 0.0 <= conf <= 1.0
    assert pytest.approx(sum(probas.values()), 0.01) == 1.0
    assert conf == max(probas.values())


def test_compute_bootstrap_cis():
    y_true = ["bug", "feature", "question"] * 20
    y_pred = ["bug", "feature", "question"] * 20
    repos = ["repo/a", "repo/b"] * 30

    cis = compute_bootstrap_cis(
        y_true=y_true,
        y_pred=y_pred,
        repos=repos,
        n_bootstraps=50,
        seed=42,
    )
    assert "macro_f1" in cis
    assert cis["macro_f1"]["score"] == 1.0
    assert cis["macro_f1"]["ci_95"][0] <= 1.0
    assert cis["macro_f1"]["ci_95"][1] <= 1.0


def test_e1_results_json():
    results_path = Path(__file__).resolve().parent.parent / "results" / "e1_results.json"
    assert results_path.exists(), "results/e1_results.json must exist"

    with open(results_path, encoding="utf-8") as f:
        e1 = json.load(f)

    assert e1["experiment"] == "E1"
    assert e1["model"] == "M1_TFIDF_LogisticRegression"
    assert e1["test_sample_count"] == 1500
    assert "f1" in e1["macro_metrics"]

    macro_f1 = e1["macro_metrics"]["f1"]
    assert "score" in macro_f1
    assert "ci_95" in macro_f1
    assert len(macro_f1["ci_95"]) == 2
    assert macro_f1["ci_95"][0] <= macro_f1["score"] <= macro_f1["ci_95"][1]
