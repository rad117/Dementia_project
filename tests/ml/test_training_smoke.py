"""End-to-end smoke test for the training pipeline against the REAL dataset.

Skipped automatically wherever data/adresso2021/ doesn't exist -- e.g. any
CI environment, since the private dataset is never committed. A green run
of this test only ever happens locally with the real data present; it must
never be read as "the real model was validated" (that requires actually
looking at the reported metrics -- see the plan's verification section).
"""

from pathlib import Path

import pytest

from ml.training.train_baseline import run_training

pytestmark = pytest.mark.skipif(
    not Path("data/adresso2021").exists(),
    reason="real ADReSSo dataset not present locally",
)


def test_train_baseline_runs_end_to_end_and_saves_artifacts(tmp_path):
    model_dir = tmp_path / "baseline_v1"
    # Reuses the real feature cache if one already exists locally (from a
    # prior `python -m ml.training.train_baseline` run) so this test doesn't
    # re-decode all 165 audio files (~3-4 min) on every run; falls back to
    # building it fresh into tmp_path if no cache exists yet.
    default_cache = Path("data/adresso2021_features_cache.csv")
    cache_path = default_cache if default_cache.exists() else tmp_path / "features_cache.csv"

    summary = run_training(model_dir=model_dir, cache_path=cache_path)

    assert summary["selected_model"] in {"logreg", "rf"}
    for name in ("logreg", "rf"):
        metrics = summary["metrics"][name]
        for key in (
            "accuracy",
            "precision",
            "recall",
            "specificity",
            "f1",
            "roc_auc",
            "confusion_matrix",
            "class_distribution",
            "cv_roc_auc_scores",
            "cv_roc_auc_mean",
        ):
            assert key in metrics

    assert (model_dir / "pipeline_logreg.joblib").exists()
    assert (model_dir / "pipeline_rf.joblib").exists()
    assert (model_dir / "feature_names.json").exists()
    assert (model_dir / "metrics.json").exists()
    assert (model_dir / "metadata.json").exists()
    assert cache_path.exists()
