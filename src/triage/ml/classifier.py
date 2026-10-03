"""M1 Classifier: TF-IDF (word and char n-grams) + Logistic Regression.

Per Section 6:
- Input: issue title and body.
- Output: probabilities for bug, feature, question.
- Confidence: highest class probability.
- Saved artifacts: models/classifier.joblib, models/classifier_meta.json.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from triage.ml.preprocess import preprocess_text

CLASSES = ["bug", "feature", "question"]


def build_m1_pipeline() -> Pipeline:
    """Build the feature extraction and classification pipeline."""
    word_vec = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=25000,
        sublinear_tf=True,
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=25000,
        sublinear_tf=True,
    )
    features = FeatureUnion(
        [
            ("word", word_vec),
            ("char", char_vec),
        ]
    )
    clf = LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    )
    return Pipeline(
        [
            ("features", features),
            ("clf", clf),
        ]
    )


class M1Classifier:
    """Wrapper for the M1 triage classifier."""

    def __init__(self, pipeline: Pipeline | None = None) -> None:
        self.pipeline = pipeline or build_m1_pipeline()
        self.classes_: list[str] = CLASSES

    def fit(self, texts: list[str], labels: list[str]) -> "M1Classifier":
        """Fit model on preprocessed text samples."""
        self.pipeline.fit(texts, labels)
        self.classes_ = [str(c) for c in self.pipeline.classes_]
        return self

    def predict(self, texts: list[str]) -> list[str]:
        """Predict labels for preprocessed text samples."""
        preds = self.pipeline.predict(texts)
        return [str(p) for p in preds]

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        """Predict probability distributions across classes."""
        return self.pipeline.predict_proba(texts)

    def predict_issue(
        self,
        title: str,
        body: str,
    ) -> tuple[str, float, dict[str, float]]:
        """Preprocess and predict label, confidence, and class probabilities.

        Returns:
            tuple of (predicted_label, confidence, proba_dict)
        """
        text = preprocess_text(title, body)
        probas = self.predict_proba([text])[0]
        prob_dict = {cls_name: float(p) for cls_name, p in zip(self.classes_, probas, strict=False)}

        max_idx = int(np.argmax(probas))
        pred_label = self.classes_[max_idx]
        confidence = float(probas[max_idx])

        return pred_label, confidence, prob_dict

    def save(
        self,
        model_path: Path | str,
        meta_path: Path | str | None = None,
        extra_meta: dict[str, Any] | None = None,
    ) -> None:
        """Serialize model weights and metadata."""
        m_path = Path(model_path)
        m_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, m_path)

        if meta_path:
            meta_p = Path(meta_path)
            meta = {
                "model_name": "M1_TFIDF_LogisticRegression",
                "saved_at": datetime.now(UTC).isoformat(),
                "classes": self.classes_,
                "extra": extra_meta or {},
            }
            with open(meta_p, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

    @classmethod
    def load(cls, model_path: Path | str) -> "M1Classifier":
        """Load trained model from joblib file."""
        m_path = Path(model_path)
        pipeline = joblib.load(m_path)
        instance = cls(pipeline=pipeline)
        instance.classes_ = [str(c) for c in pipeline.classes_]
        return instance


def compute_data_hash(file_path: Path | str) -> str:
    """Compute sha256 checksum of training data file."""
    p = Path(file_path)
    if not p.exists():
        return ""
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
