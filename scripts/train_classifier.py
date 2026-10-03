"""Train M1 Classifier on the training split only.

Strictly follows:
- Rule D3: Trained on data/train.csv only. Validated on data/val.csv.
           Never reads test set.
- Section 6.5: Saves models/classifier.joblib and models/classifier_meta.json.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sklearn import __version__ as sklearn_version
from sklearn.metrics import classification_report, f1_score

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from triage.data.loaders import load_dataset
from triage.ml.classifier import M1Classifier, compute_data_hash
from triage.ml.preprocess import preprocess_text


def train_m1(
    train_path: Path | str | None = None,
    val_path: Path | str | None = None,
    output_model_path: Path | str | None = None,
    output_meta_path: Path | str | None = None,
) -> None:
    root = Path(__file__).resolve().parent.parent
    if train_path is None:
        train_path = root / "data" / "train.csv"
    if val_path is None:
        val_path = root / "data" / "val.csv"
    if output_model_path is None:
        output_model_path = root / "models" / "classifier.joblib"
    if output_meta_path is None:
        output_meta_path = root / "models" / "classifier_meta.json"

    train_path = Path(train_path)
    val_path = Path(val_path)
    output_model_path = Path(output_model_path)
    output_meta_path = Path(output_meta_path)

    print(f"Loading train split from {train_path}...")
    train_df = load_dataset(train_path)
    train_texts = [
        preprocess_text(str(t), str(b))
        for t, b in zip(train_df["title"], train_df["body"].fillna(""), strict=False)
    ]
    train_labels = train_df["label"].tolist()

    print(f"Training M1 on {len(train_texts)} samples across 5 repositories...")
    model = M1Classifier()
    model.fit(train_texts, train_labels)

    # Evaluate on val set
    val_scores = {}
    if val_path.exists():
        print(f"Evaluating on validation split from {val_path}...")
        val_df = load_dataset(val_path)
        val_texts = [
            preprocess_text(str(t), str(b))
            for t, b in zip(val_df["title"], val_df["body"].fillna(""), strict=False)
        ]
        val_labels = val_df["label"].tolist()
        val_preds = model.predict(val_texts)

        macro_f1 = float(f1_score(val_labels, val_preds, average="macro"))
        report_dict = classification_report(val_labels, val_preds, output_dict=True)
        val_scores = {
            "val_count": len(val_labels),
            "macro_f1": macro_f1,
            "report": report_dict,
        }
        print(f"Validation Macro F1: {macro_f1:.4f}")

    meta = {
        "train_samples": len(train_texts),
        "train_data_file": str(train_path.name),
        "train_data_hash": compute_data_hash(train_path),
        "sklearn_version": sklearn_version,
        "pandas_version": pd.__version__,
        "trained_at": datetime.now(UTC).isoformat(),
        "val_scores": val_scores,
    }

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(
        model_path=output_model_path,
        meta_path=output_meta_path,
        extra_meta=meta,
    )
    print(f"Model saved to {output_model_path}")
    print(f"Metadata saved to {output_meta_path}")


if __name__ == "__main__":
    train_m1()
