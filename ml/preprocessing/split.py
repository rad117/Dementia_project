"""Participant-level splitting utilities.

Written group-aware even though today's dataset has exactly one recording
per participant (so a naive row-level split would happen to be safe too) --
this protects against silently reintroducing speaker leakage if
multi-recording data ever arrives (CONTEXT.md Section 8).
"""

import pandas as pd
from sklearn.model_selection import GroupKFold, GroupShuffleSplit


def participant_train_test_split(
    manifest: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits manifest into (train, test), guaranteeing every participant_id
    appears in only one of the two splits."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(manifest, groups=manifest["participant_id"]))
    train_df = manifest.iloc[train_idx].reset_index(drop=True)
    test_df = manifest.iloc[test_idx].reset_index(drop=True)
    return train_df, test_df


def grouped_kfold(manifest: pd.DataFrame, n_splits: int = 5):
    """Yields (train_idx, val_idx) pairs from GroupKFold keyed on
    participant_id, for use in a cross-validation loop."""
    gkf = GroupKFold(n_splits=n_splits)
    return list(gkf.split(manifest, groups=manifest["participant_id"]))
