"""Create stratified train and validation splits from official benchmark training data.

Strictly follows:
- Rule D2: Stable issue_id generation.
- Rule D3: 80% train / 20% val stratified split; never read test split outside run_eval.py.
- Rule D5: Verifies real counts per repo and per class and saves data report.
"""

import json
import sys
from pathlib import Path

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.data.loaders import add_issue_ids, create_train_val_split, load_dataset


def make_splits(
    data_dir: Path | None = None,
    results_dir: Path | None = None,
    seed: int = 42,
) -> None:
    root = Path(__file__).resolve().parent.parent
    if data_dir is None:
        data_dir = root / "data"
    if results_dir is None:
        results_dir = root / "results"

    results_dir.mkdir(parents=True, exist_ok=True)

    train_raw_path = data_dir / "issues_train.csv"
    if not train_raw_path.exists():
        raise FileNotFoundError(f"{train_raw_path} not found. Run scripts/download_data.py first.")

    print(f"Loading official training set from {train_raw_path}...")
    df_raw = load_dataset(train_raw_path)
    df_with_ids = add_issue_ids(df_raw)

    # Check for issue_id uniqueness
    unique_ids = df_with_ids["issue_id"].nunique()
    total_rows = len(df_with_ids)
    print(f"Loaded {total_rows} rows. Unique issue_ids: {unique_ids}.")
    if unique_ids != total_rows:
        print(f"Warning: {total_rows - unique_ids} duplicate issue_ids detected.")

    # Create stratified train (80%) and val (20%) split
    train_df, val_df = create_train_val_split(df_with_ids, val_ratio=0.2, seed=seed)

    # Verify no data leakage between train and val
    train_id_set = set(train_df["issue_id"])
    val_id_set = set(val_df["issue_id"])
    overlap = train_id_set.intersection(val_id_set)
    assert len(overlap) == 0, (
        f"Critical error: {len(overlap)} issue IDs overlap between train and val!"
    )

    # Save splits
    train_out = data_dir / "train.csv"
    val_out = data_dir / "val.csv"
    train_df.to_csv(train_out, index=False)
    val_df.to_csv(val_out, index=False)
    print(f"Saved {len(train_df)} train issues to {train_out}")
    print(f"Saved {len(val_df)} val issues to {val_out}")

    # Compute statistics for data_report.json
    repos = sorted(df_raw["repo"].unique().tolist())
    labels = sorted(df_raw["label"].unique().tolist())

    repo_counts = df_raw["repo"].value_counts().to_dict()
    label_counts = df_raw["label"].value_counts().to_dict()

    repo_label_breakdown = {}
    for repo in repos:
        repo_df = df_raw[df_raw["repo"] == repo]
        repo_label_breakdown[repo] = repo_df["label"].value_counts().to_dict()

    train_breakdown = {}
    for repo in repos:
        r_df = train_df[train_df["repo"] == repo]
        train_breakdown[repo] = r_df["label"].value_counts().to_dict()

    val_breakdown = {}
    for repo in repos:
        r_df = val_df[val_df["repo"] == repo]
        val_breakdown[repo] = r_df["label"].value_counts().to_dict()

    # Verify D5 criteria
    # Expected: 300 per repository and 100 per class per repository in training set
    d5_confirmed = True
    d5_notes = []
    for repo in repos:
        if repo_counts.get(repo) != 300:
            d5_confirmed = False
            d5_notes.append(f"Repo {repo} has count {repo_counts.get(repo)}, expected 300")
        for label in labels:
            c = repo_label_breakdown[repo].get(label, 0)
            if c != 100:
                d5_confirmed = False
                d5_notes.append(f"Repo {repo} label {label} has count {c}, expected 100")

    report = {
        "dataset_name": "NLBSE'24 Issue Report Classification",
        "official_training_set": {
            "total_count": total_rows,
            "unique_issue_ids": unique_ids,
            "repositories": repos,
            "labels": labels,
            "counts_per_repo": repo_counts,
            "counts_per_label": label_counts,
            "counts_per_repo_and_label": repo_label_breakdown,
        },
        "stratified_splits": {
            "seed": seed,
            "train_count": len(train_df),
            "val_count": len(val_df),
            "train_per_repo_and_label": train_breakdown,
            "val_per_repo_and_label": val_breakdown,
        },
        "section_4_2_D5_verification": {
            "expected_per_repo": 300,
            "expected_per_class_per_repo": 100,
            "confirmed": d5_confirmed,
            "notes": d5_notes
            if d5_notes
            else ["Counts match Section 4.2 D5 expectations exactly."],
        },
    }

    report_path = results_dir / "data_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Data report written to {report_path}")
    print(f"Section 4.2 D5 Confirmed: {d5_confirmed}")


if __name__ == "__main__":
    make_splits()
