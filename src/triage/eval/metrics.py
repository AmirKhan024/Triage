"""Evaluation metrics and bootstrap confidence interval computation.

Per Section 10.2 V-5:
Every reported score carries a 95% bootstrap confidence interval
(BOOTSTRAP_SAMPLES resamples of the evaluated issues).
"""

from typing import Any

import numpy as np
from sklearn.metrics import f1_score, precision_recall_fscore_support

CLASSES = ["bug", "feature", "question"]


def calculate_metrics_dict(
    y_true: list[str] | np.ndarray,
    y_pred: list[str] | np.ndarray,
    repos: list[str] | np.ndarray,
    classes: list[str] = CLASSES,
) -> dict[str, Any]:
    """Compute point estimates for overall, per-class, and per-repo metrics."""
    y_t = np.array(y_true)
    y_p = np.array(y_pred)
    rep = np.array(repos)

    # Overall macro metrics
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_t, y_p, average="macro", zero_division=0
    )

    # Per-class metrics
    p_per_class, r_per_class, f1_per_class, support_per_class = precision_recall_fscore_support(
        y_t, y_p, labels=classes, zero_division=0
    )
    per_class = {}
    for i, cls_name in enumerate(classes):
        per_class[cls_name] = {
            "precision": float(p_per_class[i]),
            "recall": float(r_per_class[i]),
            "f1": float(f1_per_class[i]),
            "support": int(support_per_class[i]),
        }

    # Per-repository metrics
    unique_repos = sorted(set(rep))
    per_repo = {}
    for r in unique_repos:
        mask = rep == r
        if np.sum(mask) > 0:
            r_f1 = float(f1_score(y_t[mask], y_p[mask], average="macro", zero_division=0))
            per_repo[r] = {
                "macro_f1": r_f1,
                "count": int(np.sum(mask)),
            }

    return {
        "macro_f1": float(macro_f1),
        "macro_precision": float(macro_p),
        "macro_recall": float(macro_r),
        "per_class": per_class,
        "per_repo": per_repo,
    }


def compute_bootstrap_cis(
    y_true: list[str] | np.ndarray,
    y_pred: list[str] | np.ndarray,
    repos: list[str] | np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
    classes: list[str] = CLASSES,
) -> dict[str, Any]:
    """Compute 95% bootstrap confidence intervals for all metrics."""
    y_t = np.array(y_true)
    y_p = np.array(y_pred)
    rep = np.array(repos)
    n_samples = len(y_t)

    # Point estimates
    point = calculate_metrics_dict(y_t, y_p, rep, classes=classes)

    rng = np.random.RandomState(seed)

    boot_macro_f1 = []
    boot_macro_p = []
    boot_macro_r = []

    unique_repos = sorted(set(rep))
    boot_repo_f1 = {r: [] for r in unique_repos}
    boot_class_f1 = {c: [] for c in classes}
    boot_class_p = {c: [] for c in classes}
    boot_class_r = {c: [] for c in classes}

    for _ in range(n_bootstraps):
        idx = rng.choice(n_samples, size=n_samples, replace=True)
        sub_yt = y_t[idx]
        sub_yp = y_p[idx]
        sub_rep = rep[idx]

        # Macro
        mp, mr, mf1, _ = precision_recall_fscore_support(
            sub_yt, sub_yp, average="macro", zero_division=0
        )
        boot_macro_f1.append(mf1)
        boot_macro_p.append(mp)
        boot_macro_r.append(mr)

        # Per-class
        cp, cr, cf1, _ = precision_recall_fscore_support(
            sub_yt, sub_yp, labels=classes, zero_division=0
        )
        for i, c in enumerate(classes):
            boot_class_p[c].append(cp[i])
            boot_class_r[c].append(cr[i])
            boot_class_f1[c].append(cf1[i])

        # Per-repo
        for r in unique_repos:
            r_mask = sub_rep == r
            if np.sum(r_mask) > 0:
                rf1 = f1_score(sub_yt[r_mask], sub_yp[r_mask], average="macro", zero_division=0)
                boot_repo_f1[r].append(rf1)
            else:
                boot_repo_f1[r].append(0.0)

    def ci(arr: list[float]) -> list[float]:
        return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]

    results = {
        "macro_f1": {
            "score": point["macro_f1"],
            "ci_95": ci(boot_macro_f1),
        },
        "macro_precision": {
            "score": point["macro_precision"],
            "ci_95": ci(boot_macro_p),
        },
        "macro_recall": {
            "score": point["macro_recall"],
            "ci_95": ci(boot_macro_r),
        },
        "per_class": {},
        "per_repo": {},
    }

    for c in classes:
        results["per_class"][c] = {
            "f1": {
                "score": point["per_class"][c]["f1"],
                "ci_95": ci(boot_class_f1[c]),
            },
            "precision": {
                "score": point["per_class"][c]["precision"],
                "ci_95": ci(boot_class_p[c]),
            },
            "recall": {
                "score": point["per_class"][c]["recall"],
                "ci_95": ci(boot_class_r[c]),
            },
            "support": point["per_class"][c]["support"],
        }

    for r in unique_repos:
        results["per_repo"][r] = {
            "macro_f1": {
                "score": point["per_repo"][r]["macro_f1"],
                "ci_95": ci(boot_repo_f1[r]),
            },
            "count": point["per_repo"][r]["count"],
        }

    return results
