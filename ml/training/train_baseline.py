"""Trains and evaluates the acoustics-only baseline classifier.

Run as: python -m ml.training.train_baseline

Pipeline: dataset manifest -> acoustic features (cached to disk) ->
participant-level train/test split -> Logistic Regression + Random Forest,
each cross-validated with GroupKFold -> full metric report on the held-out
test split for both models -> artifacts saved under models/baseline_v1/.

Acoustics-only this round -- ASR (ml/asr/) now exists standalone but isn't
fused in here yet; NLP/semantic layer (ml/nlp/) still unbuilt. See
CONTEXT.md Sections 5, 9, 12.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.stats import mannwhitneyu
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features.acoustic import extract_features
from ml.preprocessing.manifest import build_manifest
from ml.preprocessing.split import grouped_kfold, participant_train_test_split

METADATA_COLUMNS = {
    "participant_id",
    "filepath",
    "label",
    "label_binary",
    "instructor_removed",
    "severity",
}
_PAUSE_RELATED_COLUMNS = [
    "pause_count",
    "total_pause_duration_seconds",
    "pause_ratio",
    "voiced_rate_per_min",
]


def _build_or_load_features(manifest: pd.DataFrame, cache_path: Path, *, force: bool = False) -> pd.DataFrame:
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        if set(cached["filepath"]) == set(manifest["filepath"]):
            return cached

    meta = manifest.drop(columns=["duration_seconds", "sample_rate"])
    records = []
    for _, row in meta.iterrows():
        feats = extract_features(Path(row["filepath"]))
        records.append({**row.to_dict(), **feats})
    features_df = pd.DataFrame(records)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(cache_path, index=False)
    return features_df


def _confound_check(features_df: pd.DataFrame) -> dict:
    """Compares pause-related features between instructor-removed and
    unedited recordings within the Dementia class only. Report-only -- this
    documents a possible artifact, it does not correct for it."""
    dementia = features_df[features_df["label"] == "Dementia"]
    with_edit = dementia[dementia["instructor_removed"]]
    without_edit = dementia[~dementia["instructor_removed"]]

    report = {
        "n_instructor_removed": int(len(with_edit)),
        "n_unedited": int(len(without_edit)),
        "features": {},
    }
    for col in _PAUSE_RELATED_COLUMNS:
        if len(with_edit) < 2 or len(without_edit) < 2:
            report["features"][col] = {"note": "insufficient samples for a statistical test"}
            continue
        stat, p_value = mannwhitneyu(with_edit[col], without_edit[col], alternative="two-sided")
        report["features"][col] = {
            "mean_instructor_removed": float(with_edit[col].mean()),
            "mean_unedited": float(without_edit[col].mean()),
            "mannwhitney_u": float(stat),
            "p_value": float(p_value),
        }
    return report


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    roc_auc = float(roc_auc_score(y_true, y_prob)) if len(set(y_true)) > 1 else None
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(specificity),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": roc_auc,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "class_distribution": {str(k): int(v) for k, v in pd.Series(y_true).value_counts().items()},
    }


def _run_cv(estimator, X: np.ndarray, y: np.ndarray, groups: pd.Series, n_splits: int) -> list[float]:
    scores = []
    for train_idx, val_idx in grouped_kfold(pd.DataFrame({"participant_id": groups}), n_splits=n_splits):
        fold_model = clone(estimator).fit(X[train_idx], y[train_idx])
        y_prob = fold_model.predict_proba(X[val_idx])[:, 1]
        if len(set(y[val_idx])) > 1:
            scores.append(float(roc_auc_score(y[val_idx], y_prob)))
    return scores


def run_training(
    data_root: Path = Path("data/adresso2021"),
    model_dir: Path = Path("models/baseline_v1"),
    cache_path: Path = Path("data/adresso2021_features_cache.csv"),
    test_size: float = 0.2,
    cv_splits: int = 5,
    random_state: int = 42,
    force_recompute_features: bool = False,
) -> dict:
    manifest = build_manifest(data_root)
    if len(manifest) == 0:
        raise RuntimeError(f"No .wav files found under {data_root} -- is the dataset present?")

    features_df = _build_or_load_features(manifest, cache_path, force=force_recompute_features)
    confound_report = _confound_check(features_df)

    train_df, test_df = participant_train_test_split(
        features_df, test_size=test_size, random_state=random_state
    )
    feature_names = [c for c in features_df.columns if c not in METADATA_COLUMNS]

    X_train = train_df[feature_names].to_numpy(dtype=float)
    y_train = train_df["label_binary"].to_numpy()
    groups_train = train_df["participant_id"]
    X_test = test_df[feature_names].to_numpy(dtype=float)
    y_test = test_df["label_binary"].to_numpy()

    candidates = {
        "logreg": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
            ]
        ),
        "rf": RandomForestClassifier(class_weight="balanced", random_state=random_state),
    }

    results = {}
    for name, estimator in candidates.items():
        cv_scores = _run_cv(estimator, X_train, y_train, groups_train, n_splits=cv_splits)
        fitted = clone(estimator).fit(X_train, y_train)
        y_pred = fitted.predict(X_test)
        y_prob = fitted.predict_proba(X_test)[:, 1]
        metrics = _compute_metrics(y_test, y_pred, y_prob)
        metrics["cv_roc_auc_scores"] = cv_scores
        metrics["cv_roc_auc_mean"] = float(np.mean(cv_scores)) if cv_scores else None
        results[name] = {"estimator": fitted, "metrics": metrics}

    selected_name = max(
        results, key=lambda n: results[n]["metrics"]["cv_roc_auc_mean"] or float("-inf")
    )

    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, r in results.items():
        joblib.dump(r["estimator"], model_dir / f"pipeline_{name}.joblib")
    (model_dir / "feature_names.json").write_text(json.dumps(feature_names, indent=2))
    (model_dir / "metrics.json").write_text(
        json.dumps({name: r["metrics"] for name, r in results.items()}, indent=2)
    )
    (model_dir / "confound_report.json").write_text(json.dumps(confound_report, indent=2))
    metadata = {
        "selected_model": selected_name,
        "model_version": f"baseline-{selected_name}-v1",
        "trained_at": datetime.now(UTC).isoformat(),
        "sklearn_version": sklearn.__version__,
        "n_train": len(train_df),
        "n_test": len(test_df),
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    return {
        "selected_model": selected_name,
        "metrics": {name: r["metrics"] for name, r in results.items()},
        "confound_report": confound_report,
        "metadata": metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/adresso2021"))
    parser.add_argument("--model-dir", type=Path, default=Path("models/baseline_v1"))
    parser.add_argument("--cache-path", type=Path, default=Path("data/adresso2021_features_cache.csv"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--force-recompute-features", action="store_true")
    args = parser.parse_args()

    summary = run_training(
        data_root=args.data_root,
        model_dir=args.model_dir,
        cache_path=args.cache_path,
        test_size=args.test_size,
        cv_splits=args.cv_splits,
        random_state=args.random_state,
        force_recompute_features=args.force_recompute_features,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
