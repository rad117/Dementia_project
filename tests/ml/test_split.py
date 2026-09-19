import pandas as pd

from ml.preprocessing.split import grouped_kfold, participant_train_test_split


def _fake_manifest_with_repeated_participants():
    # Simulates a future multi-recording dataset: each participant has
    # 3 rows. If splitting were done row-wise instead of group-wise, a
    # participant's rows could land on both sides of a split -- this is
    # exactly the leakage CONTEXT.md Section 8 forbids.
    rows = []
    for participant_num in range(20):
        participant_id = f"adrso{participant_num:03d}"
        label = "Dementia" if participant_num % 2 == 0 else "Normal"
        for recording_num in range(3):
            rows.append(
                {
                    "participant_id": participant_id,
                    "filepath": f"data/{participant_id}_{recording_num}.wav",
                    "label": label,
                    "label_binary": 1 if label == "Dementia" else 0,
                }
            )
    return pd.DataFrame(rows)


def test_participant_train_test_split_never_splits_a_participant():
    manifest = _fake_manifest_with_repeated_participants()

    train_df, test_df = participant_train_test_split(manifest, test_size=0.3, random_state=0)

    train_participants = set(train_df["participant_id"])
    test_participants = set(test_df["participant_id"])
    assert train_participants.isdisjoint(test_participants)
    assert len(train_df) + len(test_df) == len(manifest)


def test_grouped_kfold_never_splits_a_participant_across_folds():
    manifest = _fake_manifest_with_repeated_participants()

    folds = grouped_kfold(manifest, n_splits=4)

    assert len(folds) == 4
    for train_idx, val_idx in folds:
        train_participants = set(manifest.iloc[train_idx]["participant_id"])
        val_participants = set(manifest.iloc[val_idx]["participant_id"])
        assert train_participants.isdisjoint(val_participants)
