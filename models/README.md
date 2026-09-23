# Trained model artifacts

Committed to the repo (small enough not to need git-lfs — the whole
directory is well under 1MB). `ml/inference/predict.py` loads these
in-process; there is no external model registry or download step.

- `baseline_v1/` — acoustics-only baseline. `selected_model: "logreg"`,
  `model_version: "baseline-logreg-v1"`. Kept as the explicit-`model_dir`
  fallback path in `predict.py`, and because
  `backend/services/results_mapper.py`'s `_resolve_model_dir()` scans every
  subdirectory under `models/` at runtime to explain historical assessment
  rows scored by whichever model version was live at the time.
- `baseline_v2/` — live default, fused ASR+NLP+acoustic features.
  `selected_model: "rf"`, `model_version: "baseline-rf-v2-fused"`,
  `review_threshold: 0.58` (Youden's index on the holdout test split).

Each version directory has:
- `pipeline_<selected_model>.joblib` — the trained sklearn pipeline
  (`joblib`-serialized), loaded directly.
- `metadata.json` — which pipeline file is selected, model version string,
  training timestamp, sklearn version, train/test split sizes, review
  threshold and how it was derived.
- `feature_names.json` — the exact feature-vector column order the
  pipeline expects; drives whether `predict.py` runs the ASR/NLP branch
  (present if any `asr_*`/NLP column appears) or stays acoustics-only.
- `metrics.json`, `confound_report.json` — evaluation output from training.

`predict.py`'s default is `model_dir=Path("models/baseline_v2")`; pass
`model_dir=Path("models/baseline_v1")` explicitly to use the acoustics-only
fallback. Retraining (`python -m ml.training.train_baseline
--use-asr-nlp-features --model-dir models/baseline_v2
--model-version-tag v2-fused`, see `docs/NEXT_STEPS.md`) overwrites a
version directory in place — commit the result if it should become the new
live artifact.
