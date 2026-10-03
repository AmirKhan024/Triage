"""Tests for data utilities and Stage 0 verification."""

import json
from pathlib import Path

import pandas as pd
import pytest

from triage.data.ids import generate_issue_id
from triage.data.loaders import add_issue_ids, create_train_val_split, load_dataset


def test_generate_issue_id_determinism():
    id1 = generate_issue_id("repo/test", "title", "body", "2026-01-01 10:00:00")
    id2 = generate_issue_id("repo/test", "title", "body", "2026-01-01 10:00:00")
    assert id1 == id2
    assert len(id1) == 16


def test_generate_issue_id_distinctness_and_timestamps():
    id1 = generate_issue_id("repo/test", "title", "body", "2026-01-01 10:00:00")
    id2 = generate_issue_id("repo/test", "title", "body", "2026-01-01 10:05:00")
    assert id1 != id2

    # Different repos
    id3 = generate_issue_id("repo/test2", "title", "body")
    id4 = generate_issue_id("repo/test", "title", "body")
    assert id3 != id4


def test_add_issue_ids():
    df = pd.DataFrame(
        [
            {"repo": "a/b", "title": "t1", "body": "b1", "label": "bug"},
            {"repo": "a/b", "title": "t2", "body": "b2", "label": "feature"},
        ]
    )
    df_with_ids = add_issue_ids(df)
    assert "issue_id" in df_with_ids.columns
    assert df_with_ids["issue_id"].nunique() == 2


def test_load_dataset_missing_column(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("repo,title\na/b,t1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        load_dataset(bad_csv)


def test_create_train_val_split_disjoint_and_stratified():
    # 5 repos, 3 labels, 10 items each = 150 items
    records = []
    for r in ["r1", "r2"]:
        for lbl in ["bug", "feature", "question"]:
            for i in range(10):
                records.append(
                    {
                        "repo": r,
                        "label": lbl,
                        "title": f"title_{r}_{lbl}_{i}",
                        "body": f"body_{i}",
                        "created_at": f"2026-01-0{i + 1} 12:00:00",
                    }
                )
    df = pd.DataFrame(records)
    train_df, val_df = create_train_val_split(df, val_ratio=0.2, seed=42)

    assert len(train_df) + len(val_df) == len(df)
    # Check 0 overlap
    train_ids = set(train_df["issue_id"])
    val_ids = set(val_df["issue_id"])
    assert len(train_ids.intersection(val_ids)) == 0

    # 10 items per group with 0.2 val_ratio -> 2 in val, 8 in train
    for r in ["r1", "r2"]:
        for lbl in ["bug", "feature", "question"]:
            val_group_count = len(val_df[(val_df["repo"] == r) & (val_df["label"] == lbl)])
            train_group_count = len(train_df[(train_df["repo"] == r) & (train_df["label"] == lbl)])
            assert val_group_count == 2
            assert train_group_count == 8


def test_data_report_json():
    report_path = Path(__file__).resolve().parent.parent / "results" / "data_report.json"
    assert report_path.exists(), "results/data_report.json does not exist"

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    assert report["official_training_set"]["total_count"] == 1500
    assert report["official_training_set"]["unique_issue_ids"] == 1500
    assert report["stratified_splits"]["train_count"] == 1200
    assert report["stratified_splits"]["val_count"] == 300
    assert report["section_4_2_D5_verification"]["confirmed"] is True
